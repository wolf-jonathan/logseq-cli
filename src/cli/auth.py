from __future__ import annotations

from typing import Annotated, Optional

import httpx
import typer

from src.config import get_config_path, get_token, set_token, get_server, set_server, _validate_server as _validate_server_url, _normalize_server_url

app = typer.Typer(no_args_is_help=True, help="Manage Logseq API connection settings.")

DEFAULT_SERVER = "http://127.0.0.1:12315"


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


def _check_connectivity(url: str) -> bool:
    """Check connectivity to Logseq server. Returns True if reachable."""
    try:
        with httpx.Client(base_url=url, timeout=3) as client:
            response = client.get("/api")
            return response.status_code in (200, 400, 401, 403, 405)
    except (httpx.ConnectError, httpx.ReadTimeout):
        return False


def _get_current_graph(base_url: str, token: str) -> dict | None:
    """Call logseq.App.getCurrentGraph and return graph info or None on failure."""
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.post(
                "/api",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={"method": "logseq.App.getCurrentGraph", "args": []},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "name" in data:
                return data
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
        pass
    return None


@app.command("set-token")
def auth_set_token(
    token: Annotated[
        Optional[str],
        typer.Argument(help="Logseq API token. If omitted, you will be prompted securely."),
    ] = None,
) -> None:
    value = (token or typer.prompt("Logseq API token", hide_input=True)).strip()
    path = set_token(value)
    typer.echo("Stored Logseq API token")
    typer.echo(f"Config path: {path}")


@app.command("set-server")
def auth_set_server(
    server: Annotated[
        str,
        typer.Argument(help="Logseq HTTP server URL (default: http://127.0.0.1:12315). Examples: http://10.0.0.1:12315, https://example.com", callback=_validate_server),
    ],
) -> None:
    # Normalize to full URL
    base_url = _normalize_server_url(server)

    # Pre-save connectivity check
    connected = _check_connectivity(base_url)
    if not connected:
        typer.echo(
            f"Warning: Cannot connect to Logseq at {base_url}. "
            f"Is Logseq running and reachable?",
            err=True,
        )
        if not typer.confirm("Save this server address anyway?", default=False):
            typer.echo("Server address not saved.")
            raise typer.Exit(0)

    path = set_server(server)
    typer.echo(f"Stored Logseq server: {server}")
    typer.echo(f"Config path: {path}")

    if not connected:
        typer.echo("Connection: not verified (Logseq not reachable at time of saving)")
        return

    typer.echo("Connection: OK")

    # Get current graph info
    token = get_token()
    graph = _get_current_graph(base_url, token) if token else None

    if graph:
        typer.echo("")
        typer.echo(f"Current Graph:")
        typer.echo(f"  Name: {graph.get('name', 'N/A')}")
        typer.echo(f"  Path: {graph.get('path', 'N/A')}")
        typer.echo("")
        if not typer.confirm("Is this the correct graph?", default=True):
            typer.echo("Server address saved, but you may want to check your Logseq configuration.")
    else:
        typer.echo("Warning: Could not retrieve current graph info (missing token or API error)")


@app.command("status")
def auth_status() -> None:
    token = get_token()
    server = get_server() or DEFAULT_SERVER
    typer.echo(f"Config path: {get_config_path()}")
    typer.echo(f"Stored token: {_mask_token(token)}")
    typer.echo(f"Server: {server}")
    if not token:
        typer.echo("Run `logseq auth set-token` to store a token.")
