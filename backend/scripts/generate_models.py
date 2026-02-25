"""Generate db/models.py from the migrated database schema.

Connects to the SQLite DB (after migrations are applied), introspects all
tables via sqlalchemy.inspect, and emits a typed ORM module with
relationships.

Usage:
    python scripts/generate_models.py            # writes db/models.py
    python scripts/generate_models.py --stdout   # print to stdout instead
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = BACKEND_ROOT / "db"
OUTPUT_FILE = DB_DIR / "models.py"

# Relationships that cannot be inferred from FKs alone.
# Format: (parent_table, child_table, parent_attr, child_attr, order_by)
RELATIONSHIPS = [
    ("rakeback_participants", "eligibility_rules", "eligibility_rules", "participant", "created_at"),
    ("block_snapshots", "delegation_entries", "delegations", "snapshot", "delegator_address"),
    ("block_yields", "yield_sources", "yield_sources", "block_yield", "subnet_id"),
    ("conversion_events", "tao_allocations", "allocations", "conversion_event", None),
]

# Map SQL type strings to SQLAlchemy imports
TYPE_MAP = {
    "TEXT": "String",
    "INTEGER": "Integer",
    "BIGINT": "BigInteger",
    "NUMERIC": "Numeric",
    "DATE": "Date",
    "BOOLEAN": "Boolean",
    "REAL": "Float",
}

# Tables to skip generating models for
SKIP_TABLES = {"_migrations"}

HEADER = '''\
"""SQLAlchemy ORM models — auto-generated from migrated schema.

DO NOT EDIT by hand. Re-generate with:
    python scripts/generate_models.py
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from db.enums import (
    AggregationMode,
    AllocationMethod,
    CompletenessFlag,
    DataSource,
    DelegationType,
    GapType,
    ParticipantType,
    PartnerType,
    PaymentStatus,
    PeriodType,
    ResolutionStatus,
    RunStatus,
    RunType,
)


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

'''


def _get_db_url() -> str:
    for candidate in (BACKEND_ROOT / ".env", BACKEND_ROOT.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
    db_path = os.environ.get("DB_SQLITE_PATH", "data/rakeback.db")
    if not os.path.isabs(db_path):
        db_path = str(BACKEND_ROOT / db_path)
    return f"sqlite:///{db_path}"


def _table_to_class(table_name: str) -> str:
    """Convert snake_case table name to PascalCase class name."""
    parts = table_name.split("_")
    return "".join(p.capitalize() for p in parts)


def _sql_type_to_sa(col) -> str:
    """Convert an inspected column type to a SQLAlchemy type string."""
    type_str = str(col["type"]).upper()

    if "NUMERIC" in type_str:
        # Preserve precision: NUMERIC(38, 18) -> Numeric(38, 18)
        return type_str.replace("NUMERIC", "Numeric")
    if "VARCHAR" in type_str or "TEXT" in type_str:
        return "String"
    if "BIGINT" in type_str:
        return "BigInteger"
    if "INTEGER" in type_str or "INT" in type_str:
        return "Integer"
    if "DATE" == type_str:
        return "Date"
    if "BOOLEAN" in type_str:
        return "Boolean"
    if "REAL" in type_str or "FLOAT" in type_str:
        return "Float"
    return "String"


def generate(engine) -> str:
    """Generate the models module source from the DB schema."""
    insp = inspect(engine)
    tables = [t for t in insp.get_table_names() if t not in SKIP_TABLES]

    lines = [HEADER]

    for table in tables:
        columns = insp.get_columns(table)
        pk_cols = insp.get_pk_constraint(table)
        fks = insp.get_foreign_keys(table)
        uniques = insp.get_unique_constraints(table)
        indexes = insp.get_indexes(table)

        class_name = _table_to_class(table)
        lines.append(f"class {class_name}(Base):")
        lines.append(f'    __tablename__ = "{table}"')
        lines.append("")

        pk_names = set(pk_cols["constrained_columns"]) if pk_cols else set()

        # Build FK lookup: column -> (ref_table, ref_col)
        simple_fks = {}
        composite_fks = []
        for fk in fks:
            if len(fk["constrained_columns"]) == 1:
                simple_fks[fk["constrained_columns"][0]] = (
                    fk["referred_table"],
                    fk["referred_columns"][0],
                    fk.get("options", {}).get("ondelete"),
                )
            else:
                composite_fks.append(fk)

        # Columns
        for col in columns:
            name = col["name"]
            sa_type = _sql_type_to_sa(col)
            parts = [f"    {name}: Mapped"]

            is_pk = name in pk_names
            nullable = col.get("nullable", True) and not is_pk
            kwargs = []

            # Type annotation
            if sa_type in ("String", "Text"):
                py_type = "str | None" if nullable else "str"
            elif sa_type in ("Integer", "BigInteger"):
                py_type = "int | None" if nullable else "int"
            elif "Numeric" in sa_type:
                py_type = "float | None" if nullable else "float"
            elif sa_type == "Date":
                py_type = "str | None" if nullable else "str"
            elif sa_type == "Boolean":
                py_type = "bool | None" if nullable else "bool"
            else:
                py_type = "str | None" if nullable else "str"

            # mapped_column args
            mc_args = []
            if name in simple_fks:
                ref_table, ref_col, ondelete = simple_fks[name]
                fk_str = f'ForeignKey("{ref_table}.{ref_col}"'
                if ondelete:
                    fk_str += f', ondelete="{ondelete}"'
                fk_str += ")"
                mc_args.append(fk_str)

            mc_kwargs = []
            if is_pk:
                mc_kwargs.append("primary_key=True")
            if not nullable and not is_pk:
                mc_kwargs.append("nullable=False")
            if col.get("default") is not None:
                default = col["default"]
                if isinstance(default, str):
                    # Strip wrapping quotes from SQLite defaults like "'CHAIN'"
                    clean = default.strip("'\"")
                    # Escape inner quotes for valid Python
                    clean = clean.replace('"', '\\"')
                    mc_kwargs.append(f'default="{clean}"')
                else:
                    mc_kwargs.append(f"default={default}")

            all_args = mc_args + mc_kwargs
            single = f"    {name}: Mapped[{py_type}] = mapped_column({', '.join(all_args)})"
            if len(single) <= 99:
                lines.append(single)
            else:
                lines.append(f"    {name}: Mapped[{py_type}] = mapped_column(")
                for i, arg in enumerate(all_args):
                    comma = "," if i < len(all_args) - 1 else ","
                    lines.append(f"        {arg}{comma}")
                lines.append("    )")

        # Composite FK constraints
        if composite_fks:
            lines.append("")
            for cfk in composite_fks:
                cols = cfk["constrained_columns"]
                ref_table = cfk["referred_table"]
                ref_cols = cfk["referred_columns"]
                ondelete = cfk.get("options", {}).get("ondelete", "")
                cols_str = ", ".join(f'"{c}"' for c in cols)
                refs_str = ", ".join(f'"{ref_table}.{rc}"' for rc in ref_cols)
                fkc = f"    __table_args__ = (ForeignKeyConstraint([{cols_str}], [{refs_str}]"
                if ondelete:
                    fkc += f', ondelete="{ondelete}"'
                fkc += "),"

        # Table args: unique constraints + composite FKs
        table_args_parts = []
        for cfk in composite_fks:
            cols = cfk["constrained_columns"]
            ref_table = cfk["referred_table"]
            ref_cols = cfk["referred_columns"]
            ondelete = cfk.get("options", {}).get("ondelete", "")
            cols_str = ", ".join(f'"{c}"' for c in cols)
            refs_str = ", ".join(f'"{ref_table}.{rc}"' for rc in ref_cols)
            fkc = f"ForeignKeyConstraint([{cols_str}], [{refs_str}]"
            if ondelete:
                fkc += f', ondelete="{ondelete}"'
            fkc += ")"
            table_args_parts.append(fkc)

        for uq in uniques:
            cols_str = ", ".join(f'"{c}"' for c in uq["column_names"])
            uq_name = uq.get("name")
            if uq_name and uq_name != "None" and str(uq_name) != "None":
                uqc = f'UniqueConstraint({cols_str}, name="{uq_name}")'
            else:
                uqc = f"UniqueConstraint({cols_str})"
            table_args_parts.append(uqc)

        if table_args_parts:
            lines.append("")
            lines.append("    __table_args__ = (")
            for part in table_args_parts:
                # Break long lines
                if len(f"        {part},") > 99:
                    # Split into multi-line
                    lines.append(f"        {part.split('(')[0]}(")
                    inner = part.split("(", 1)[1].rstrip(")")
                    for arg in inner.split(", "):
                        lines.append(f"            {arg},")
                    lines.append("        ),")
                else:
                    lines.append(f"        {part},")
            lines.append("    )")

        # Relationships
        for parent_table, child_table, parent_attr, child_attr, order_by in RELATIONSHIPS:
            if table == parent_table:
                child_class = _table_to_class(child_table)
                rel_lines = [
                    f"    {parent_attr} = relationship(",
                    f'        "{child_class}",',
                    f'        back_populates="{child_attr}",',
                    '        cascade="all, delete-orphan",',
                ]
                if order_by:
                    rel_lines.append(f'        order_by="{order_by}",')
                rel_lines.append("    )")
                lines.extend(rel_lines)
            elif table == child_table:
                parent_class = _table_to_class(parent_table)
                lines.append(
                    f"    {child_attr} = relationship("
                    f'"{parent_class}", back_populates="{parent_attr}")'
                )

        lines.append("")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate db/models.py from migrated schema")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing file")
    args = parser.parse_args()

    url = _get_db_url()
    engine = create_engine(url)

    # Verify tables exist
    insp = inspect(engine)
    tables = insp.get_table_names()
    if not tables or tables == ["_migrations"]:
        print("ERROR: No tables found. Run migrations first: python migrations/migrate.py", file=sys.stderr)
        sys.exit(1)

    source = generate(engine)

    if args.stdout:
        print(source)
    else:
        OUTPUT_FILE.write_text(source)
        print(f"Generated {OUTPUT_FILE} ({len(tables)} tables)")


if __name__ == "__main__":
    main()
