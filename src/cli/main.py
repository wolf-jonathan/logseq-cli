from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

import httpx
import typer
from dotenv import load_dotenv

from src.logseq_client import LogseqClient
from src.logseq_service import LogseqService
from src import __version__
from src.config import get_token, get_host, get_port
from src.cli import auth as auth_module
from src.cli import page as page_module
from src.cli import block as block_module
from src.cli import graph as graph_module
from src.cli import query as query_module
from src.cli import skill as skill_module

load_dotenv()


def configure_windows_stdio_utf8() -> None:
    if os.name != "nt":
        return

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


configure_windows_stdio_utf8()

app = typer.Typer(no_args_is_help=True)
app.add_typer(auth_module.app, name="auth")
app.add_typer(page_module.app, name="page")
app.add_typer(block_module.app, name="block")
app.add_typer(graph_module.app, name="graph")
app.add_typer(query_module.app, name="query")
app.add_typer(skill_module.app, name="skill")


@app.command("version")
def version() -> None:
    typer.echo(__version__)


def get_service() -> LogseqService:
    token = os.environ.get("LOGSEQ_TOKEN")
    if not token:
        token = get_token()
        if not token:
            typer.echo("Error: no Logseq API token is configured.", err=True)
            typer.echo("", err=True)
            typer.echo("Set one with:", err=True)
            typer.echo("  logseq auth set-token", err=True)
            typer.echo("", err=True)
            typer.echo("Environment variable override is still supported:", err=True)
            typer.echo("  LOGSEQ_TOKEN=***", err=True)
            raise typer.Exit(1)
    host = os.environ.get("LOGSEQ_HOST") or get_host()
    port_str = os.environ.get("LOGSEQ_PORT")
    port = int(port_str) if port_str else get_port()
    return LogseqService(LogseqClient(token=token, host=host, port=port))


def handle_errors(fn):
    """Decorator for subcommand callbacks to catch httpx errors gracefully."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except httpx.ConnectError:
            typer.echo("Error: Cannot connect to Logseq. Is it running?", err=True)
            raise typer.Exit(1)
        except httpx.HTTPStatusError as e:
            typer.echo(
                f"Error: Logseq API error (status {e.response.status_code}): {e}",
                err=True,
            )
            raise typer.Exit(1)

    return wrapper


if __name__ == "__main__":
    app()
