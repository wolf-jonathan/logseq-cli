from __future__ import annotations

import httpx
from typing import Annotated, Optional

import typer

from src.config import get_config_path, get_token, set_token, get_server, set_server, _parse_server

app = typer.Typer(no_args_is_help=True, help="Manage Logseq API connection settings.")


def _validate_server(value: str) -> str:
    """Validate server string (host:port format)."""
    try:
        _parse_server(value)
    except ValueError as e:
        raise typer.BadParameter(str(e))
    return value


def _mask_token(token: str | None) -> str:
    if not token:
        return "missing"
    if len(token) <= 4:
        return "*" * len(token)
    return "*" * (len(token) - 4) + token[-4:]


def _check_connectivity(host: str, port: int) -> bool:
    """Return True if Logseq responds on the given host:port."""
    try:
        with httpx.Client(base_url=f"http://{host}:{port}", timeout=3) as client:
            resp = client.get("/api")
            return resp.status_code in (200, 400, 401, 403, 405)
    except httpx.RequestError:
        return False


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


@app.command("set-server")
def auth_set_server(
    server: Annotated[
        str,
        typer.Argument(help="Logseq HTTP server address in 'host:port' format (default: 127.0.0.1:12315).", callback=_validate_server),
    ],
) -> None:
    host, port = _parse_server(server)

    # Pre-save connectivity check
    if not _check_connectivity(host, port):
        typer.echo(
            f"Warning: Cannot connect to Logseq at {host}:{port}. "
            f"Is Logseq running and reachable?",
            err=True,
        )
        if not typer.confirm("Save this server address anyway?", default=False):
            typer.echo("Server address not saved.")
            raise typer.Exit(0)

    path = set_server(server)
    typer.echo(f"Stored Logseq server: {server}")
    typer.echo(f"Config path: {path}")


@app.command("status")
def auth_status() -> None:
    token = get_token()
    typer.echo(f"Config path: {get_config_path()}")
    typer.echo(f"Stored token: {_mask_token(token)}")
    typer.echo(f"Server: {get_server()}")
    if not token:
        typer.echo("Run `logseq auth set-token` to store a token.")
