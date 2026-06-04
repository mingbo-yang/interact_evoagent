"""evoagent memory — manage memories."""

import typer

from evoagent.cli.main import memory_app


@memory_app.command("list")
def memory_list(
    memory_type: str = typer.Option(None, "--type", help="Filter by type: working, episodic, semantic, procedural, reflection."),
    limit: int = typer.Option(20, "--limit", help="Max memories to show."),
):
    """List stored memories."""
    from evoagent.memory.schema import MemoryType
    from evoagent.memory.sqlite_store import SQLiteMemoryStore

    store = SQLiteMemoryStore()
    mt = MemoryType(memory_type) if memory_type else None
    items = store.list(memory_type=mt, limit=limit)

    if not items:
        typer.echo("No memories found.")
        store.close()
        return

    for item in items:
        typer.echo(f"[{item.memory_type.value}] {item.id}: {item.content[:100]}")
    store.close()


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query."),
    top_k: int = typer.Option(5, "--top-k", help="Number of results."),
    memory_type: str = typer.Option(None, "--type", help="Filter by type."),
):
    """Search memories by keyword."""
    from evoagent.memory.schema import MemoryType
    from evoagent.memory.sqlite_store import SQLiteMemoryStore

    store = SQLiteMemoryStore()
    mt = [MemoryType(memory_type)] if memory_type else None
    results = store.search(query, memory_types=mt, top_k=top_k)

    if not results:
        typer.echo("No matches.")
        store.close()
        return

    for r in results:
        typer.echo(f"[{r.memory_type.value}] {r.content[:120]} (imp={r.importance:.1f})")
    store.close()
