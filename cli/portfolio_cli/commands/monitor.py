import typer
from rich.console import Console
from rich.panel import Panel

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("status")
def status():
    """Check the current health of the portfolio website."""
    try:
        data = api.get("/monitor/status")

        if "message" in data:
            console.print(f"[dim]{data['message']}[/]")
            return

        is_up = data.get("is_up", False)
        color = "green" if is_up else "red"
        indicator = "● ONLINE" if is_up else "● OFFLINE"

        lines = [
            f"[bold {color}]{indicator}[/]",
            f"URL:          [dim]{data.get('url', '—')}[/]",
            f"Status Code:  {data.get('status_code') or '—'}",
            f"Response:     {data.get('response_time_ms') or '—'} ms",
            f"SSL Expiry:   {data.get('ssl_expiry_days') or '—'} days",
            f"Checked:      [dim]{(data.get('checked_at') or '')[:19]}[/]",
        ]
        if data.get("error"):
            lines.append(f"Error:        [red]{data['error']}[/]")

        console.print(
            Panel("\n".join(lines), title="SITE HEALTH", border_style=color)
        )
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")


@app.command("check")
def run_check():
    """Trigger an immediate health check via the agent."""
    try:
        result = api.post(
            "/agent/chat",
            body={"message": "Run a health check on my portfolio site now."},
        )
        console.print(result.get("reply", "Done."))
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")