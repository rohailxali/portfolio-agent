import typer
from rich.console import Console
from rich.table import Table

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_leads(
    status: str = typer.Option(None, "--status", "-s", help="Filter by status."),
    page: int = typer.Option(1, "--page", "-p"),
):
    """List contact form leads."""
    try:
        params: dict[str, str | int] = {"page": page}
        if status:
            params["status"] = status
        leads = api.get("/leads", params=params)

        if not leads:
            console.print("[dim]No leads found.[/]")
            return

        table = Table(show_header=True, header_style="bold dim")
        table.add_column("ID",     style="dim",   width=10)
        table.add_column("NAME",   width=18)
        table.add_column("EMAIL",  width=26)
        table.add_column("CLASS",  width=8)
        table.add_column("STATUS", width=12)
        table.add_column("DATE",   width=12)

        class_colors = {
            "hot": "red", "warm": "yellow",
            "cold": "blue", "spam": "dim",
        }

        for lead in leads:
            cls = lead.get("classification") or "—"
            color = class_colors.get(cls, "white")
            table.add_row(
                lead["id"][:8],
                lead["name"],
                lead["email"],
                f"[{color}]{cls}[/]",
                lead["status"],
                lead["created_at"][:10],
            )

        console.print(table)
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")


@app.command("classify")
def classify(lead_id: str = typer.Argument(..., help="Lead ID to classify.")):
    """Run AI classification on a lead."""
    try:
        result = api.post(f"/leads/{lead_id}/classify")
        cls = result.get("classification", "unknown")
        class_colors = {"hot": "red", "warm": "yellow", "cold": "blue", "spam": "dim"}
        color = class_colors.get(cls, "white")
        console.print(
            f"[{color}]{cls.upper()}[/] — {result.get('reasoning', '')}"
        )
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")
        raise typer.Exit(1)


@app.command("status")
def set_status(
    lead_id: str = typer.Argument(...),
    status: str = typer.Argument(..., help="new | classified | contacted | converted | spam"),
):
    """Update the status of a lead."""
    try:
        api.patch(f"/leads/{lead_id}/status", body={"status": status})
        console.print(f"[green]✓[/] Lead [cyan]{str(lead_id)[:8]}[/] status → [bold]{status}[/]")  # type: ignore
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")
        raise typer.Exit(1)