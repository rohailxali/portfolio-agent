import typer
from rich.console import Console
from rich.prompt import Prompt

from portfolio_cli import client as api
from portfolio_cli.config import (
    save_token, clear_token, get_api_url, set_api_url, get_token
)

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("login")
def login(
    email: str = typer.Option(None, "--email", "-e", help="Your email address."),
    api_url: str = typer.Option(None, "--api-url", help="Override API base URL."),
):
    """Authenticate and store credentials securely."""
    if api_url:
        set_api_url(api_url)

    if not email:
        email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    try:
        data = api.post(
            "/auth/login",
            body={"email": email, "password": password},
            auth=False,
        )
        save_token(data["access_token"])
        console.print(f"\n[bold green]✓[/] Authenticated as [cyan]{email}[/]")
        console.print(f"  API: [dim]{get_api_url()}[/]")
    except api.ApiError as e:
        console.print(f"[bold red]✗[/] Login failed: {e.detail}")
        raise typer.Exit(1)


@app.command("logout")
def logout():
    """Revoke session and clear stored token."""
    try:
        api.post("/auth/logout")
    except Exception:
        pass
    clear_token()
    console.print("[bold green]✓[/] Logged out.")


@app.command("whoami")
def whoami():
    """Show the currently authenticated user."""
    try:
        me = api.get("/auth/me")
        console.print(f"[bold]{me['email']}[/] [dim]({me['role']})[/]")
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")
        raise typer.Exit(1)


@app.command("config")
def config(
    api_url: str = typer.Option(None, "--api-url", help="Set the API base URL."),
):
    """View or update CLI configuration."""
    if api_url:
        set_api_url(api_url)
        console.print(f"[green]✓[/] API URL set to [cyan]{api_url}[/]")
    else:
        console.print(f"API URL: [cyan]{get_api_url()}[/]")
        token = get_token()
        console.print(f"Token:   {'[green]stored[/]' if token else '[red]not set[/]'}")