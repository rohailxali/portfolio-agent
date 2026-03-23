import typer
from rich.console import Console

from portfolio_cli.commands import auth, agent, deploy, leads, logs, monitor, memory

app = typer.Typer(
    name="portfolio",
    help="Portfolio Agent CLI — control your portfolio from the terminal.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

app.add_typer(auth.app,    name="auth",    help="Authentication commands.")
app.add_typer(agent.app,   name="agent",   help="Chat with the AI agent.")
app.add_typer(deploy.app,  name="deploy",  help="Manage deployments.")
app.add_typer(leads.app,   name="leads",   help="View and manage leads.")
app.add_typer(logs.app,    name="logs",    help="Query audit logs.")
app.add_typer(monitor.app, name="monitor", help="Check website health.")
app.add_typer(memory.app,  name="memory",  help="Read and write agent memory.")


@app.command("version")
def version():
    """Show CLI version."""
    console.print("[bold amber]portfolio-cli[/] v1.0.0")


if __name__ == "__main__":
    app()