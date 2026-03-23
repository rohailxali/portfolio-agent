import typer
from rich.console import Console
from rich.table import Table

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_logs(
    page: int = typer.Option(1, "--page", "-p"),
    action: str = typer.Option(None, "--action", "-a", help="Filter by action prefix."),
    resource: str = typer.Option(None, "--resource", "-r", help="Filter by resource_type."),
    raw: bool = typer.Option(False, "--raw", help="Print raw JSON output."),
):
    """Query the audit log."""
    try:
        params = {"page": page}
        if action:
            params["action"] = action
        if resource:
            params["resource_type"] = resource
        data = api.get("/logs", params=params)
        logs = data.get("logs", [])

        if not logs:
            console.print("[dim]No log entries found.[/]")
            return

        if raw:
            import json
            console.print(json.dumps(logs, indent=2))
            return

        table = Table(show_header=True, header_style="bold dim", show_lines=False)
        table.add_column("TIMESTAMP",     width=20)
        table.add_column("ACTION",        style="cyan",  width=28)
        table.add_column("RESOURCE",      width=22)
        table.add_column("IP",            style="dim", width=16)

        for log in logs:
            table.add_row(
                log["created_at"][:19],
                log["action"],
                f"{log.get('resource_type') or ''}:{(log.get('resource_id') or '')[:8]}".strip(":"),
                log.get("ip_address") or "—",
            )

        console.print(table)
        console.print(f"[dim]Page {page} — {len(logs)} entries[/]")
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")