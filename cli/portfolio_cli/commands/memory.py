import json
import typer
from rich.console import Console
from rich.table import Table

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_memory():
    """List all stored memory keys."""
    try:
        data = api.get("/memory")
        if not data:
            console.print("[dim]No memory entries.[/]")
            return
        table = Table(show_header=True, header_style="bold dim")
        table.add_column("KEY",      style="cyan", width=30)
        table.add_column("CATEGORY", width=12)
        table.add_column("VALUE",    width=50)
        for row in data:
            table.add_row(
                row["key"],
                row.get("category") or "—",
                str(row["value"])[:80],
            )
        console.print(table)
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")


@app.command("get")
def get_memory(key: str = typer.Argument(..., help="Memory key to retrieve.")):
    """Get a single memory value by key."""
    try:
        data = api.get(f"/memory/{key}")
        console.print(json.dumps(data, indent=2))
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")


@app.command("set")
def set_memory(
    key: str = typer.Argument(...),
    value: str = typer.Argument(..., help="Value (JSON string or plain text)."),
    category: str = typer.Option("preference", "--category", "-c"),
):
    """Set a memory key-value pair."""
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    try:
        api.post(
            "/agent/chat",
            body={
                "message": (
                    f"Write to memory: key='{key}', "
                    f"value={json.dumps(parsed_value)}, "
                    f"category='{category}', confirm=true"
                )
            },
        )
        console.print(f"[green]✓[/] Memory set: [cyan]{key}[/] = {parsed_value}")
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")