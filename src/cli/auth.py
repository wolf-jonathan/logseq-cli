from __future__ import annotations

from typing import Annotated, Optional

import typer

from src.config import get_config_path, get_token, set_token, get_host, set_host, get_port, set_port

app = typer.Typer(no_args_is_help=True, help="Manage Logseq API connection settings.")

MIN_PORT = 1
MAX_PORT = 65535


def _validate_port(value: str) -> int:
    """Validate that a port string is a valid integer within 1-65535."""
    try:
        port = int(value)
    except ValueError:
        raise typer.BadParameter(f"'{value}' is not a valid integer.")
    if port < MIN_PORT or port > MAX_PORT:
        raise typer.BadParameter(
            f"Port must be between {MIN_PORT} and {MAX_PORT}, got {port}."
        )
    return port


def _mask_token(token: str | None) -> str:
    if not token:
        return "missing"
    if len(token) <= 4:
        return "*" * len(token)
    return "*" * (len(token) - 4) + token[-4:]


@app.command("set-token")
def auth_set_token(
    token: Annotated[
        Optional[str],
        typer.Argument(help="Logseq API token. If omitted, you will be prompted securely."),
    ] = None,
) -> None:
    value = token or typer.prompt("Logseq API token", hide_input=True)
    path = set_token(value)
    typer.echo("Stored Logseq API token")
    typer.echo(f"Config path: {path}")


@app.command("set-host")
def auth_set_host(
    host: Annotated[
        str,
        typer.Argument(help="Logseq HTTP server host (default: 127.0.0.1)."),
    ],
) -> None:
    path = set_host(host)
    typer.echo(f"Stored Logseq host: {host}")
    typer.echo(f"Config path: {path}")


@app.command("set-port")
def auth_set_port(
    port: Annotated[
        int,
        typer.Argument(help="Logseq HTTP server port (default: 12315).", callback=_validate_port),
    ],
) -> None:
    path = set_port(port)
    typer.echo(f"Stored Logseq port: {port}")
    typer.echo(f"Config path: {path}")


@app.command("status")
def auth_status() -> None:
    token = get_token()
    typer.echo(f"Config path: {get_config_path()}")
    typer.echo(f"Stored token: {_mask_token(token)}")
    typer.echo(f"Host: {get_host()}")
    typer.echo(f"Port: {get_port()}")
    if not token:
        typer.echo("Run `logseq auth set-token` to store a token.")
