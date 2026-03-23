import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from portfolio_cli import client as api

app = typer.Typer(no_args_is_help=True)
console = Console()

_conversation_id: str | None = None


@app.command("chat")
def chat(
    message: str = typer.Argument(None, help="Message to send. Omit for interactive mode."),
    new: bool = typer.Option(False, "--new", "-n", help="Start a new conversation."),
):
    """
    Chat with the Portfolio Agent.

    Run without arguments for interactive REPL mode.
    Pass a message as an argument for a single-shot query.
    """
    global _conversation_id

    if new:
        _conversation_id = None

    if message:
        _send(message)
    else:
        console.print(
            Panel(
                "[dim]Type your message and press Enter. "
                "Type [bold]/exit[/] to quit, [bold]/new[/] to start fresh.[/]",
                title="[amber]PORTFOLIO AGENT[/]",
                border_style="dim",
            )
        )
        while True:
            try:
                msg = console.input("[bold amber]›[/] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Bye.[/]")
                break

            if not msg:
                continue
            if msg == "/exit":
                break
            if msg == "/new":
                _conversation_id = None
                console.print("[dim]New conversation started.[/]")
                continue

            _send(msg)


def _send(message: str) -> None:
    global _conversation_id
    try:
        payload: dict = {"message": message}
        if _conversation_id:
            payload["conversation_id"] = _conversation_id

        res = api.post("/agent/chat", body=payload)
        _conversation_id = res["conversation_id"]

        # Print tool calls as dim indicators
        for tc in res.get("tool_calls", []):
            console.print(f"  [dim]⚙ {tc['tool']}[/]")

        # Print agent reply
        console.print(Markdown(res["reply"]))

        # Handle confirmation gate
        if res.get("requires_confirmation") and res.get("pending_action"):
            pa = res["pending_action"]
            console.print(
                Panel(
                    f"[bold yellow]⚠ CONFIRMATION REQUIRED[/]\n\n"
                    f"{pa['confirmation_message']}\n\n"
                    f"Tool: [cyan]{pa['tool_name']}[/]",
                    border_style="yellow",
                )
            )
            confirmed = Confirm.ask("Proceed?", default=False)
            if confirmed:
                confirm_res = api.post(
                    "/agent/chat",
                    body={
                        "message": f"Confirmed. Proceed with {pa['tool_name']}.",
                        "conversation_id": _conversation_id,
                        "confirm_pending": True,
                        "pending_action": pa,
                    },
                )
                console.print(Markdown(confirm_res["reply"]))
            else:
                console.print("[dim]Action cancelled.[/]")

    except api.ApiError as e:
        console.print(f"[bold red]Error {e.status}:[/] {e.detail}")


@app.command("history")
def history(limit: int = typer.Option(10, "--limit", "-l")):
    """List recent conversations."""
    try:
        convos = api.get("/agent/conversations")
        if not convos:
            console.print("[dim]No conversations yet.[/]")
            return
        for c in convos[:limit]:
            console.print(
                f"[cyan]{c['id'][:8]}[/]  [dim]{c['created_at'][:19]}[/]"
            )
    except api.ApiError as e:
        console.print(f"[red]{e.detail}[/]")