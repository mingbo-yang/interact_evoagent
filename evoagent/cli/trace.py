"""evoagent trace — view execution traces."""

import json
from pathlib import Path

import typer

from evoagent.cli.main import trace_app


@trace_app.command("list")
def trace_list():
    """List all recorded runs."""
    runs_dir = Path(".runs")
    if not runs_dir.exists():
        typer.echo("No .runs directory found. Run an agent first.")
        return

    runs = sorted(d for d in runs_dir.iterdir() if d.is_dir())
    if not runs:
        typer.echo("No traces found.")
        return

    for r in runs:
        meta_path = r / "metadata.json"
        task = ""
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                task = meta.get("task", "")[:80]
            except Exception:
                pass
        typer.echo(f"{r.name}  {task}")


@trace_app.command("show")
def trace_show(
    run_id: str = typer.Argument(..., help="Run ID to show."),
):
    """Show run metadata and event summary."""
    run_dir = Path(".runs") / run_id
    if not run_dir.exists():
        typer.echo(f"Run '{run_id}' not found.")
        raise typer.Exit(1)

    # Metadata
    meta_path = run_dir / "metadata.json"
    if meta_path.exists():
        typer.echo("=== Metadata ===")
        typer.echo(meta_path.read_text())

    # Event summary
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        typer.echo("\n=== Event Summary ===")
        counts: dict[str, int] = {}
        with open(events_path) as f:
            for line in f:
                try:
                    evt = json.loads(line)
                    et = evt.get("event_type", "unknown")
                    counts[et] = counts.get(et, 0) + 1
                except Exception:
                    pass
        for et, cnt in sorted(counts.items()):
            typer.echo(f"  {et}: {cnt}")


@trace_app.command("events")
def trace_events(
    run_id: str = typer.Argument(..., help="Run ID."),
    event_type: str = typer.Option(None, "--type", help="Filter by event type."),
):
    """Show events from a run."""
    events_path = Path(".runs") / run_id / "events.jsonl"
    if not events_path.exists():
        typer.echo(f"No events found for run '{run_id}'.")
        return

    with open(events_path) as f:
        for line in f:
            try:
                evt = json.loads(line)
            except Exception:
                continue
            if event_type and evt.get("event_type") != event_type:
                continue
            ts = evt.get("timestamp", "")[:19]
            et = evt.get("event_type", "?")
            pl = str(evt.get("payload", ""))[:100]
            typer.echo(f"{ts}  {et:30s}  {pl}")
