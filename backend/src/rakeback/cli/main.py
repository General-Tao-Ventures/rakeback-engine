"""Main CLI entry point."""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="rakeback",
    help="Validator Rakeback Attribution Engine CLI",
    add_completion=False
)

console = Console()


def parse_block_range(block_range: str) -> tuple[int, int]:
    """Parse block range string like '1000:2000'."""
    try:
        parts = block_range.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise typer.BadParameter(
            f"Invalid block range '{block_range}'. Expected format: START:END (e.g., 1000:2000)"
        )


def parse_month(month_str: str) -> tuple[int, int]:
    """Parse month string like '2026-01'."""
    try:
        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise typer.BadParameter(
            f"Invalid month '{month_str}'. Expected format: YYYY-MM (e.g., 2026-01)"
        )


@app.command()
def init_db(
    force: bool = typer.Option(False, "--force", "-f", help="Drop and recreate tables")
):
    """Initialize the database schema."""
    from rakeback.database import init_database, get_engine
    from rakeback.models import Base
    
    with console.status("Initializing database..."):
        if force:
            engine = get_engine()
            Base.metadata.drop_all(engine)
            console.print("[yellow]Dropped existing tables[/yellow]")
        
        init_database()
    
    console.print("[green]Database initialized successfully[/green]")


@app.command()
def ingest(
    block_range: str = typer.Option(..., "--block-range", "-b", help="Block range (e.g., 1000:2000)"),
    validator: str = typer.Option(..., "--validator", "-v", help="Validator hotkey"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="Skip existing blocks"),
    fail_on_error: bool = typer.Option(False, "--fail-on-error", help="Stop on first error")
):
    """Ingest block data from the chain."""
    from rakeback.database import get_session
    from rakeback.services import ChainClient, IngestionService
    
    start_block, end_block = parse_block_range(block_range)
    
    console.print(f"Ingesting blocks {start_block} to {end_block} for validator {validator[:16]}...")
    
    with get_session() as session:
        chain_client = ChainClient()
        service = IngestionService(session, chain_client)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Ingesting...", total=None)
            
            result = service.ingest_block_range(
                start_block=start_block,
                end_block=end_block,
                validator_hotkey=validator,
                skip_existing=skip_existing,
                fail_on_error=fail_on_error
            )
            
            progress.remove_task(task)
    
    # Display results
    table = Table(title="Ingestion Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Run ID", result.run_id)
    table.add_row("Blocks Processed", str(result.blocks_processed))
    table.add_row("Blocks Created", str(result.blocks_created))
    table.add_row("Blocks Skipped", str(result.blocks_skipped))
    table.add_row("Gaps Detected", str(len(result.gaps_detected)))
    table.add_row("Errors", str(len(result.errors)))
    
    console.print(table)
    
    if result.gaps_detected:
        console.print("\n[yellow]Data gaps detected:[/yellow]")
        for start, end in result.gaps_detected[:10]:
            console.print(f"  Blocks {start} - {end}")
        if len(result.gaps_detected) > 10:
            console.print(f"  ... and {len(result.gaps_detected) - 10} more")
    
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for err in result.errors[:5]:
            console.print(f"  {err}")
        if len(result.errors) > 5:
            console.print(f"  ... and {len(result.errors) - 5} more")


@app.command()
def attribute(
    block_range: str = typer.Option(..., "--block-range", "-b", help="Block range (e.g., 1000:2000)"),
    validator: str = typer.Option(..., "--validator", "-v", help="Validator hotkey"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="Skip existing blocks"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Compute without persisting")
):
    """Run attribution for a block range."""
    from rakeback.database import get_session
    from rakeback.services import AttributionEngine
    
    start_block, end_block = parse_block_range(block_range)
    
    mode = "[yellow](dry run)[/yellow]" if dry_run else ""
    console.print(f"Running attribution for blocks {start_block} to {end_block} {mode}...")
    
    with get_session() as session:
        engine = AttributionEngine(session)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Computing attributions...", total=None)
            
            result = engine.run_attribution(
                start_block=start_block,
                end_block=end_block,
                validator_hotkey=validator,
                skip_existing=skip_existing,
                dry_run=dry_run
            )
            
            progress.remove_task(task)
    
    # Display results
    table = Table(title="Attribution Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Run ID", result.run_id)
    table.add_row("Blocks Processed", str(result.blocks_processed))
    table.add_row("Attributions Created", str(result.attributions_created))
    table.add_row("Blocks Skipped", str(result.blocks_skipped))
    table.add_row("Blocks Incomplete", str(result.blocks_incomplete))
    table.add_row("Total dTAO Attributed", str(result.total_dtao_attributed))
    
    console.print(table)
    
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for err in result.errors[:5]:
            console.print(f"  {err}")


@app.command()
def aggregate(
    period_type: str = typer.Option(..., "--period-type", "-t", help="Period type: daily or monthly"),
    date_str: Optional[str] = typer.Option(None, "--date", "-d", help="Date for daily (YYYY-MM-DD)"),
    month_str: Optional[str] = typer.Option(None, "--month", "-m", help="Month for monthly (YYYY-MM)"),
    validator: str = typer.Option(..., "--validator", "-v", help="Validator hotkey")
):
    """Aggregate attributions into ledger entries."""
    from rakeback.database import get_session
    from rakeback.services import AggregationService
    from rakeback.models import PeriodType
    
    if period_type == "daily":
        if not date_str:
            raise typer.BadParameter("--date is required for daily aggregation")
        target_date = date.fromisoformat(date_str)
        console.print(f"Aggregating daily for {target_date}...")
    elif period_type == "monthly":
        if not month_str:
            raise typer.BadParameter("--month is required for monthly aggregation")
        year, month = parse_month(month_str)
        console.print(f"Aggregating monthly for {year}-{month:02d}...")
    else:
        raise typer.BadParameter("--period-type must be 'daily' or 'monthly'")
    
    with get_session() as session:
        service = AggregationService(session)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Aggregating...", total=None)
            
            if period_type == "daily":
                result = service.aggregate_daily(target_date, validator)
            else:
                result = service.aggregate_monthly(year, month, validator)
            
            progress.remove_task(task)
    
    # Display results
    table = Table(title="Aggregation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Run ID", result.run_id)
    table.add_row("Period", f"{result.period_start} to {result.period_end}")
    table.add_row("Entries Created", str(result.entries_created))
    table.add_row("Total TAO Owed", str(result.total_tao_owed))
    
    console.print(table)
    
    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warn in result.warnings:
            console.print(f"  {warn}")


@app.command()
def export(
    period_type: str = typer.Option(..., "--period-type", "-t", help="Period type: daily or monthly"),
    period_start: str = typer.Option(..., "--start", "-s", help="Period start (YYYY-MM-DD)"),
    period_end: str = typer.Option(..., "--end", "-e", help="Period end (YYYY-MM-DD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path")
):
    """Export ledger entries to CSV."""
    from rakeback.database import get_session
    from rakeback.services import ExportService
    from rakeback.models import PeriodType
    
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    ptype = PeriodType(period_type)
    
    output_path = Path(output) if output else None
    
    console.print(f"Exporting {period_type} ledger from {start} to {end}...")
    
    with get_session() as session:
        service = ExportService(session)
        
        result = service.export_ledger_csv(
            period_type=ptype,
            period_start=start,
            period_end=end,
            output_path=output_path
        )
    
    console.print(f"\n[green]Exported to: {result.output_path}[/green]")
    console.print(f"Rows: {result.row_count}")
    console.print(f"Total TAO: {result.total_tao}")
    
    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warn in result.warnings:
            console.print(f"  {warn}")


@app.command("import-override")
def import_override(
    type: str = typer.Option(..., "--type", "-t", help="Override type: snapshot or yield"),
    file: str = typer.Option(..., "--file", "-f", help="CSV file path"),
    validator: str = typer.Option(..., "--validator", "-v", help="Validator hotkey")
):
    """Import CSV override data."""
    from rakeback.database import get_session
    from rakeback.services import IngestionService
    
    file_path = Path(file)
    if not file_path.exists():
        raise typer.BadParameter(f"File not found: {file}")
    
    console.print(f"Importing {type} override from {file}...")
    
    with get_session() as session:
        service = IngestionService(session)
        
        if type == "snapshot":
            result = service.import_snapshot_csv(file_path, validator)
        elif type == "yield":
            result = service.import_yield_csv(file_path, validator)
        else:
            raise typer.BadParameter("--type must be 'snapshot' or 'yield'")
    
    console.print(f"\n[green]Import complete[/green]")
    console.print(f"Records created: {result.blocks_created}")
    
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for err in result.errors[:10]:
            console.print(f"  {err}")


@app.command()
def status():
    """Show system status and statistics."""
    from rakeback.database import get_session
    from rakeback.repositories import (
        BlockSnapshotRepository,
        BlockYieldRepository,
        BlockAttributionRepository,
        RakebackLedgerRepository,
        ProcessingRunRepository,
        DataGapRepository
    )
    from rakeback.models import RunStatus, ResolutionStatus
    
    with get_session() as session:
        snapshot_repo = BlockSnapshotRepository(session)
        yield_repo = BlockYieldRepository(session)
        attribution_repo = BlockAttributionRepository(session)
        ledger_repo = RakebackLedgerRepository(session)
        run_repo = ProcessingRunRepository(session)
        gap_repo = DataGapRepository(session)
        
        # Gather stats
        snapshot_count = snapshot_repo.count()
        yield_count = yield_repo.count()
        attribution_count = attribution_repo.count()
        ledger_count = ledger_repo.count()
        
        open_gaps = gap_repo.get_open()
        running_jobs = run_repo.get_running()
        
        unpaid_total = ledger_repo.get_total_owed(unpaid_only=True)
    
    # Display
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Count", style="green", justify="right")
    
    table.add_row("Block Snapshots", str(snapshot_count))
    table.add_row("Block Yields", str(yield_count))
    table.add_row("Attributions", str(attribution_count))
    table.add_row("Ledger Entries", str(ledger_count))
    table.add_row("Open Data Gaps", str(len(open_gaps)))
    table.add_row("Running Jobs", str(len(running_jobs)))
    
    console.print(table)
    
    console.print(f"\n[bold]Total Unpaid TAO:[/bold] {unpaid_total}")
    
    if open_gaps:
        console.print("\n[yellow]Open Data Gaps:[/yellow]")
        for gap in open_gaps[:5]:
            console.print(f"  Blocks {gap.block_start}-{gap.block_end}: {gap.reason}")
    
    if running_jobs:
        console.print("\n[blue]Running Jobs:[/blue]")
        for job in running_jobs:
            console.print(f"  {job.run_type.value}: started {job.started_at}")


@app.command("list-participants")
def list_participants(
    active_only: bool = typer.Option(True, "--active/--all", help="Show only active participants")
):
    """List all rakeback participants."""
    from rakeback.database import get_session
    from rakeback.repositories import ParticipantRepository
    
    with get_session() as session:
        repo = ParticipantRepository(session)
        
        if active_only:
            participants = repo.get_active(as_of=date.today())
        else:
            participants = repo.get_all()
    
    if not participants:
        console.print("[yellow]No participants found[/yellow]")
        return
    
    table = Table(title="Rakeback Participants")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="blue")
    table.add_column("Rakeback %", justify="right")
    table.add_column("Payout Address")
    table.add_column("Active", justify="center")
    
    for p in participants:
        is_active = "Yes" if p.is_active(date.today()) else "No"
        table.add_row(
            p.id,
            p.name,
            p.type.value if hasattr(p.type, 'value') else str(p.type),
            f"{p.rakeback_percentage:.1%}",
            p.payout_address[:16] + "..." if len(p.payout_address) > 16 else p.payout_address,
            is_active
        )
    
    console.print(table)


@app.command("add-participant")
def add_participant(
    id: str = typer.Option(..., "--id", help="Participant ID"),
    name: str = typer.Option(..., "--name", help="Participant name"),
    type: str = typer.Option(..., "--type", "-t", help="Type: partner, delegator_group, subnet"),
    rakeback_pct: float = typer.Option(..., "--rakeback", "-r", help="Rakeback percentage (0-1)"),
    payout_address: str = typer.Option(..., "--payout", "-p", help="Payout address"),
    addresses: Optional[str] = typer.Option(None, "--addresses", "-a", help="Comma-separated addresses to match")
):
    """Add a new rakeback participant."""
    from rakeback.database import get_session
    from rakeback.services.rules_engine import RulesEngine
    
    # Build matching rules
    if addresses:
        address_list = [a.strip() for a in addresses.split(",")]
        matching_rules = {"rules": [{"type": "EXACT_ADDRESS", "addresses": address_list}]}
    else:
        matching_rules = {"rules": [{"type": "ALL"}]}
    
    with get_session() as session:
        engine = RulesEngine(session)
        
        participant = engine.add_participant(
            id=id,
            name=name,
            participant_type=type,
            matching_rules=matching_rules,
            rakeback_percentage=rakeback_pct,
            payout_address=payout_address,
            effective_from=date.today()
        )
    
    console.print(f"[green]Added participant: {participant.name}[/green]")
    console.print(f"  ID: {participant.id}")
    console.print(f"  Rakeback: {participant.rakeback_percentage:.2%}")


if __name__ == "__main__":
    app()
