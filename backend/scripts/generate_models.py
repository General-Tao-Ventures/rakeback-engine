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
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
DB_DIR: Path = BACKEND_ROOT / "db"
OUTPUT_FILE: Path = DB_DIR / "models.py"

# Relationships that cannot be inferred from FKs alone.
# Format: (parent_table, child_table, parent_attr, child_attr, order_by)
RELATIONSHIPS: list[tuple[str, str, str, str, str | None]] = [
    (
        "rakeback_participants",
        "eligibility_rules",
        "eligibility_rules",
        "participant",
        "created_at",
    ),
    ("block_snapshots", "delegation_entries", "delegations", "snapshot", "delegator_address"),
    ("block_yields", "yield_sources", "yield_sources", "block_yield", "subnet_id"),
    ("conversion_events", "tao_allocations", "allocations", "conversion_event", None),
]

# Map SQL type strings to SQLAlchemy imports
TYPE_MAP: dict[str, str] = {
    "TEXT": "String",
    "INTEGER": "Integer",
    "BIGINT": "BigInteger",
    "NUMERIC": "Numeric",
    "DATE": "Date",
    "BOOLEAN": "Boolean",
    "REAL": "Float",
}

# Tables to skip generating models for
SKIP_TABLES: set[str] = {"_migrations"}

HEADER = '''\
"""SQLAlchemy ORM models — auto-generated from migrated schema.

DO NOT EDIT by hand. Re-generate with:
    python scripts/generate_models.py
"""

from datetime import datetime, timezone
from decimal import Decimal
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
    db_path: str = os.environ.get("DB_SQLITE_PATH", "data/rakeback.db")
    if not os.path.isabs(db_path):
        db_path = str(BACKEND_ROOT / db_path)
    return f"sqlite:///{db_path}"


def _table_to_class(table_name: str) -> str:
    """Convert snake_case table name to PascalCase class name."""
    parts: list[str] = table_name.split("_")
    return "".join(p.capitalize() for p in parts)


def _sql_type_to_sa(col: dict[str, object]) -> str:
    """Convert an inspected column type to a SQLAlchemy type string."""
    type_str: str = str(col["type"]).upper()

    if "NUMERIC" in type_str:
        # Preserve precision: NUMERIC(38, 18) -> Numeric(38, 18)
        return type_str.replace("NUMERIC", "Numeric")
    if "VARCHAR" in type_str or "TEXT" in type_str:
        return "String"
    if "BIGINT" in type_str:
        return "BigInteger"
    if "INTEGER" in type_str or "INT" in type_str:
        return "Integer"
    if type_str == "DATE":
        return "Date"
    if "BOOLEAN" in type_str:
        return "Boolean"
    if "REAL" in type_str or "FLOAT" in type_str:
        return "Float"
    return "String"


def generate(engine: object) -> str:
    """Generate the models module source from the DB schema."""
    insp: object = inspect(engine)  # type: ignore[arg-type]
    tables: list[str] = [t for t in insp.get_table_names() if t not in SKIP_TABLES]  # type: ignore[union-attr]

    lines: list[str] = [HEADER]

    for table in tables:
        columns: list[dict[str, object]] = insp.get_columns(table)  # type: ignore[union-attr]
        pk_cols: dict[str, object] = insp.get_pk_constraint(table)  # type: ignore[union-attr]
        fks: list[dict[str, object]] = insp.get_foreign_keys(table)  # type: ignore[union-attr]
        uniques: list[dict[str, object]] = insp.get_unique_constraints(table)  # type: ignore[union-attr]
        class_name: str = _table_to_class(table)
        lines.append(f"class {class_name}(Base):")
        lines.append(f'    __tablename__ = "{table}"')
        lines.append("")

        pk_names: set[str] = set(pk_cols["constrained_columns"]) if pk_cols else set()  # type: ignore[arg-type]

        # Build FK lookup: column -> (ref_table, ref_col)
        simple_fks: dict[str, tuple[str, str, str | None]] = {}
        composite_fks: list[dict[str, object]] = []
        for fk in fks:
            if len(fk["constrained_columns"]) == 1:  # type: ignore[arg-type]
                simple_fks[fk["constrained_columns"][0]] = (  # type: ignore[index]
                    fk["referred_table"],  # type: ignore[assignment]
                    fk["referred_columns"][0],  # type: ignore[index]
                    fk.get("options", {}).get("ondelete"),  # type: ignore[union-attr]
                )
            else:
                composite_fks.append(fk)

        # Columns
        for col in columns:
            name: str = col["name"]  # type: ignore[assignment]
            sa_type: str = _sql_type_to_sa(col)

            is_pk: bool = name in pk_names
            nullable: bool = bool(col.get("nullable", True)) and not is_pk

            # Type annotation
            if sa_type in ("String", "Text"):
                py_type: str = "str | None" if nullable else "str"
            elif sa_type in ("Integer", "BigInteger"):
                py_type = "int | None" if nullable else "int"
            elif "Numeric" in sa_type:
                py_type = "Decimal | None" if nullable else "Decimal"
            elif sa_type == "Date":
                py_type = "str | None" if nullable else "str"
            elif sa_type == "Boolean":
                py_type = "bool | None" if nullable else "bool"
            else:
                py_type = "str | None" if nullable else "str"

            # mapped_column args
            mc_args: list[str] = []
            if name in simple_fks:
                ref_table: str
                ref_col: str
                ondelete: str | None
                ref_table, ref_col, ondelete = simple_fks[name]
                fk_str: str = f'ForeignKey("{ref_table}.{ref_col}"'
                if ondelete:
                    fk_str += f', ondelete="{ondelete}"'
                fk_str += ")"
                mc_args.append(fk_str)

            mc_kwargs: list[str] = []
            if is_pk:
                mc_kwargs.append("primary_key=True")
            if not nullable and not is_pk:
                mc_kwargs.append("nullable=False")
            if col.get("default") is not None:
                default: object = col["default"]
                if isinstance(default, str):
                    # Strip wrapping quotes from SQLite defaults like "'CHAIN'"
                    clean: str = default.strip("'\"")
                    # Use proper typed defaults for numeric columns
                    if "Numeric" in sa_type:
                        mc_kwargs.append(f"default=Decimal({clean!r})")
                    elif sa_type in ("Integer", "BigInteger"):
                        try:
                            mc_kwargs.append(f"default={int(clean)}")
                        except ValueError:
                            clean = clean.replace('"', '\\"')
                            mc_kwargs.append(f'default="{clean}"')
                    else:
                        # Escape inner quotes for valid Python
                        clean = clean.replace('"', '\\"')
                        mc_kwargs.append(f'default="{clean}"')
                else:
                    mc_kwargs.append(f"default={default}")

            all_args: list[str] = mc_args + mc_kwargs
            single: str = f"    {name}: Mapped[{py_type}] = mapped_column({', '.join(all_args)})"
            if len(single) <= 99:
                lines.append(single)
            else:
                lines.append(f"    {name}: Mapped[{py_type}] = mapped_column(")
                for i, arg in enumerate(all_args):
                    comma: str = "," if i < len(all_args) - 1 else ","
                    lines.append(f"        {arg}{comma}")
                lines.append("    )")

        # Composite FK constraints
        if composite_fks:
            lines.append("")
            for cfk in composite_fks:
                cols: object = cfk["constrained_columns"]
                cfk_ref_table: object = cfk["referred_table"]
                ref_cols: object = cfk["referred_columns"]
                cfk_ondelete: str = cfk.get("options", {}).get("ondelete", "")  # type: ignore[union-attr]
                cols_str: str = ", ".join(f'"{c}"' for c in cols)  # type: ignore[union-attr]
                refs_str: str = ", ".join(f'"{cfk_ref_table}.{rc}"' for rc in ref_cols)  # type: ignore[union-attr]
                fkc: str = f"    __table_args__ = (ForeignKeyConstraint([{cols_str}], [{refs_str}]"
                if cfk_ondelete:
                    fkc += f', ondelete="{cfk_ondelete}"'
                fkc += "),"

        # Table args: unique constraints + composite FKs
        table_args_parts: list[str] = []
        for cfk in composite_fks:
            cols = cfk["constrained_columns"]
            cfk_ref_table = cfk["referred_table"]
            ref_cols = cfk["referred_columns"]
            cfk_ondelete = cfk.get("options", {}).get("ondelete", "")  # type: ignore[union-attr]
            cols_str = ", ".join(f'"{c}"' for c in cols)  # type: ignore[union-attr]
            refs_str = ", ".join(f'"{cfk_ref_table}.{rc}"' for rc in ref_cols)  # type: ignore[union-attr]
            fkc = f"ForeignKeyConstraint([{cols_str}], [{refs_str}]"
            if cfk_ondelete:
                fkc += f', ondelete="{cfk_ondelete}"'
            fkc += ")"
            table_args_parts.append(fkc)

        for uq in uniques:
            cols_str = ", ".join(f'"{c}"' for c in uq["column_names"])  # type: ignore[union-attr]
            uq_name: object = uq.get("name")
            if uq_name and uq_name != "None" and str(uq_name) != "None":
                uqc: str = f'UniqueConstraint({cols_str}, name="{uq_name}")'
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
                    inner: str = part.split("(", 1)[1].rstrip(")")
                    for arg in inner.split(", "):
                        lines.append(f"            {arg},")
                    lines.append("        ),")
                else:
                    lines.append(f"        {part},")
            lines.append("    )")

        # Relationships
        for parent_table, child_table, parent_attr, child_attr, order_by in RELATIONSHIPS:
            if table == parent_table:
                child_class: str = _table_to_class(child_table)
                rel_lines: list[str] = [
                    f"    {parent_attr} = relationship(",
                    f'        "{child_class}",',
                    f'        back_populates="{child_attr}",',
                    '        cascade="all, delete-orphan",',
                ]
                if order_by:
                    rel_lines.append(f'        order_by="{child_class}.{order_by}",')
                rel_lines.append("    )")
                lines.extend(rel_lines)
            elif table == child_table:
                parent_class: str = _table_to_class(parent_table)
                lines.append(
                    f"    {child_attr} = relationship("
                    f'"{parent_class}", back_populates="{parent_attr}")'
                )

        lines.append("")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Generate db/models.py from migrated schema",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing file",
    )
    args: argparse.Namespace = parser.parse_args()

    url: str = _get_db_url()
    engine: object = create_engine(url)

    # Verify tables exist
    insp: object = inspect(engine)  # type: ignore[arg-type]
    tables: list[str] = insp.get_table_names()  # type: ignore[union-attr]
    if not tables or tables == ["_migrations"]:
        print(
            "ERROR: No tables found. Run migrations first: python migrations/migrate.py",
            file=sys.stderr,
        )
        sys.exit(1)

    source: str = generate(engine)

    if args.stdout:
        print(source)
    else:
        OUTPUT_FILE.write_text(source)
        print(f"Generated {OUTPUT_FILE} ({len(tables)} tables)")


if __name__ == "__main__":
    main()
