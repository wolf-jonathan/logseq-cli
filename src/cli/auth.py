from __future__ import annotations

import sys
from typing import Annotated, Optional

import httpx
import typer

from src.config import get_config_path, get_token, set_token, load_config_file_server, set_server, resolve_token, \
    _validate_server as _validate_server_url, _normalize_server_url, DEFAULT_SERVER
from src.logseq_client import LogseqClient

app = typer.Typer(no_args_is_help=True, help="Manage Logseq API connection settings.")


class TokenAuthError(Exception):
    """Token authentication failed (401/403)."""


class GraphInfoError(Exception):
    """Graph info could not be retrieved."""


def _validate_server(value: str) -> str:
    """Validate server URL string."""
    value = value.strip()
    if not value:
        raise typer.BadParameter("Server address cannot be empty.")
    try:
        _validate_server_url(value)
    except ValueError as e:
        raise typer.BadParameter(str(e))
    return value


def _mask_token(token: str | None) -> str:
    if not token:
        return "missing"
    if len(token) <= 4:
        return "*" * len(token)
    return "*" * (len(token) - 4) + token[-4:]


def _get_current_graph(base_url: str, token: str) -> dict:
    """Call logseq.App.getCurrentGraph and return graph info.
    Raises TokenAuthError on 401/403, GraphInfoError on other failures.
    """
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.post(
                base_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={"method": "logseq.App.getCurrentGraph", "args": []},
            )
            if resp.status_code in (401, 403):
                raise TokenAuthError("Token authentication failed.")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "name" in data:
                return data
            raise GraphInfoError("Invalid response from Logseq API.")
    except (TokenAuthError, GraphInfoError):
        raise
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
        raise GraphInfoError(f"Could not retrieve graph info: {e}")


@app.command("set-token")
def auth_set_token(
    token: Annotated[
        Optional[str],
        typer.Argument(help="Logseq API token. If omitted, you will be prompted securely."),
    ] = None,
) -> None:
    value = (token or typer.prompt("Logseq API token", hide_input=True)).strip()
    set_token(value)
    typer.echo("Stored Logseq API token")
    typer.echo(f"Config path: {get_config_path()}")


@app.command("set-server")
def auth_set_server(
    server: Annotated[
        str,
        typer.Argument(help=f"Logseq HTTP server URL (default: {DEFAULT_SERVER}). Examples: http://10.0.0.1:12315/api, https://example.com/api", callback=_validate_server),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-confirm graph info, skip interactive prompt"),
    ] = False,
    exact_path: Annotated[
        bool,
        typer.Option("--exact-path", help="Use the provided path exactly, do not auto-append /api"),
    ] = False,
) -> None:
    # Normalize to full URL
    base_url = _normalize_server_url(server, exact_path=exact_path)

    # Pre-save connectivity check
    connected = LogseqClient.check_connectivity(base_url)
    if not connected:
        typer.echo(
            f"Warning: Cannot connect to Logseq at {base_url}. "
            f"Is Logseq running and reachable?",
            err=True,
        )
        if not typer.confirm("Save this server address anyway?", default=False):
            typer.echo("Server address not saved.")
            raise typer.Exit(0)

    normalized_url = set_server(base_url, exact_path=exact_path)
    typer.echo(f"Stored Logseq server: {normalized_url}")
    typer.echo(f"Config path: {get_config_path()}")

    if not connected:
        typer.echo("Connection: not verified (Logseq not reachable at time of saving)")
        return

    typer.echo("Connection: OK")

    # Get current graph info
    token = resolve_token()

    if not token:
        typer.echo("Warning: No token configured. Run `logseq auth set-token` to store a token.", err=True)
        return

    try:
        graph = _get_current_graph(normalized_url, token)
    except TokenAuthError:
        typer.echo("Warning: Token authentication failed. Run `logseq auth set-token` to reconfigure.", err=True)
        return
    except GraphInfoError:
        typer.echo("Warning: Could not retrieve current graph info (API error).", err=True)
        return

    typer.echo("")
    typer.echo(f"Current Graph:")
    typer.echo(f"  Name: {graph.get('name', 'N/A')}")
    typer.echo(f"  Path: {graph.get('path', 'N/A')}")
    typer.echo("")

    if yes:
        typer.echo("Graph info auto-confirmed.")
    elif not sys.stdin.isatty():
        typer.echo("Non-interactive environment, continuing automatically.")
    else:
        typer.confirm("Is this the correct graph?", abort=True, default=True)


@app.command("status")
def auth_status() -> None:
    token = get_token()
    server = load_config_file_server() or DEFAULT_SERVER
    typer.echo(f"Config path: {get_config_path()}")
    typer.echo(f"Stored token: {_mask_token(token)}")
    typer.echo(f"Server: {server}")
    if not token:
        typer.echo("Run `logseq auth set-token` to store a token.")
