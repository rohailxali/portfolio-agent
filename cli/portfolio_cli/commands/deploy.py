import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_deploys(
    limit: int = typer.Option(10, "--limit", "-l"),
    status: str = typer.Option(None, "--status", "-s"),
):
    """List recent deployments."""
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
        data = api.get("/deploy", params=params)
        deploys = data.get("deployments", [])

        if not deploys:
            console.print("[dim]No deployments found.[/]")
            return

        table = Table(show_header=True, header_style="bold dim")
        table.add_column("ID",       style="cyan",  width=10)
        table.add_column("STATUS",   width=10)
        table.add_column("TRIGGER",  width=10)
        table.add_column("SHA",      width=9)
        table.add_column("STARTED",  width=20)

        status_styles = {
            "success": "green",
            "failed": "red",
            "running": "yellow",
            "pending": "dim",
        }

        for d in deploys:
            s = d["status"]
            style = status_styles.get(s, "white")
            table.add_row(
                d["id"][:8],
                f"[{style}]{s}[/]",
                d["trigger"],
                (d["commit_sha"] or "—")[:7],
                d["started_at"][:19],
            )

        console.print(table)
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")


@app.command("trigger")
def trigger(
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to deploy."),
    reason: str = typer.Option("Manual CLI trigger", "--reason", "-r"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
):
    """Trigger a new deployment."""
    if not yes:
        confirmed = Confirm.ask(
            f"Deploy branch [cyan]{branch}[/]?", default=False
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    try:
        result = api.post(
            "/deploy/trigger",
            body={"branch": branch, "reason": reason, "confirm": True},
        )
        if result.get("requires_confirmation"):
            console.print(f"[yellow]⚠[/] {result['message']}")
        else:
            console.print(
                f"[green]✓[/] Deployment triggered: [cyan]{result.get('deploy_id', '')[:8]}[/]"
            )
            if url := result.get("workflow_url"):
                console.print(f"  [dim]{url}[/]")
    except api.ApiError as e:
        console.print(f"[red]✗[/] {e.detail}")
        raise typer.Exit(1)


@app.command("rollback")
def rollback(
    deploy_id: str = typer.Argument(..., help="Deploy ID to roll back to."),
    reason: str = typer.Option("Manual CLI rollback", "--reason", "-r"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Roll back to a specific successful deployment."""
    if not yes:
        confirmed = Confirm.ask(
            f"Roll back to deploy [cyan]{deploy_id[:8]}[/]?", default=False
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit(0)

    try:
        result = api.post(
            "/deploy/rollback",
            body={"target_deploy_id": deploy_id, "reason": reason, "confirm": True},
        )
        if result.get("requires_confirmation"):
            console.print(f"[yellow]⚠[/] {result['message']}")
        else:
            console.print(
                f"[green]✓[/] Rollback initiated: [cyan]{result.get('rollback_id', '')[:8]}[/]"
            )
    except api.ApiError as e:
        console.print(f"[red]✗[/] {e.detail}")
        raise typer.Exit(1)


@app.command("status")
def status():
    """Show the most recent deployment status."""
    try:
        data = api.get("/deploy", params={"limit": 1})
        deploys = data.get("deployments", [])
        if not deploys:
            console.print("[dim]No deployments on record.[/]")
            return
        d = deploys[0]
        status_colors = {"success": "green", "failed": "red", "running": "yellow", "pending": "dim"}
        color = status_colors.get(d["status"], "white")
        console.print(
            f"[{color}]{d['status'].upper()}[/] — "
            f"ID: [cyan]{d['id'][:8]}[/]  "
            f"Branch: {d['trigger']}  "
            f"SHA: {(d['commit_sha'] or '—')[:7]}  "
            f"Started: {d['started_at'][:19]}"
        )
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")