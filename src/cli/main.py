from __future__ import annotations

import asyncio
import os
import re
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


def _validate_host_value(host: str) -> None:
    """Validate host value from env var. Raises typer.Exit on failure."""
    if not host or not host.strip():
        typer.echo("Error: LOGSEQ_HOST cannot be empty.", err=True)
        raise typer.Exit(1)
    if re.search(r"[\s\x00-\x1f]", host):
        typer.echo(
            f"Error: LOGSEQ_HOST must not contain spaces or control characters, got '{host}'.",
            err=True,
        )
        raise typer.Exit(1)


def _check_connectivity(host: str, port: int) -> None:
    """Pre-flight connectivity check. Raises typer.Exit if Logseq is unreachable."""
    try:
        with httpx.Client(base_url=f"http://{host}:{port}", timeout=3) as sync_client:
            response = sync_client.get("/api")
            # 200 = healthy, 400/401/403/405 = server is running (just auth/method issue)
            if response.status_code not in (200, 400, 401, 403, 405):
                typer.echo(
                    f"Error: Logseq responded with unexpected status {response.status_code} "
                    f"at {host}:{port}. Is Logseq running with the HTTP plugin enabled?",
                    err=True,
                )
                raise typer.Exit(1)
    except httpx.ConnectError:
        typer.echo(
            f"Error: Cannot connect to Logseq at {host}:{port}. "
            f"Is Logseq running and reachable?",
            err=True,
        )
        raise typer.Exit(1)
    except httpx.ReadTimeout:
        typer.echo(
            f"Error: Connection to Logseq at {host}:{port} timed out. "
            f"Is Logseq running and responsive?",
            err=True,
        )
        raise typer.Exit(1)


def get_service(check_connectivity: bool = True) -> LogseqService:
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
            typer.echo("  LOGSEQ_TOKEN=your-token-here", err=True)
            raise typer.Exit(1)
    env_host = os.environ.get("LOGSEQ_HOST")
    if env_host is not None:
        _validate_host_value(env_host)
    host = env_host or get_host()
    port = get_port()
    port_str = os.environ.get("LOGSEQ_PORT")
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            typer.echo(
                f"Error: LOGSEQ_PORT must be a valid integer between 1 and 65535, got '{port_str}'.",
                err=True,
            )
            raise typer.Exit(1)
        if port < 1 or port > 65535:
            typer.echo(
                f"Error: LOGSEQ_PORT must be between 1 and 65535, got {port}.",
                err=True,
            )
            raise typer.Exit(1)

    if check_connectivity:
        _check_connectivity(host, port)

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
