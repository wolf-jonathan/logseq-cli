from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

DEFAULT_PATH = "/api"
LEGACY_DEFAULT_PORT = 12315
DEFAULT_SERVER = f"http://127.0.0.1:{LEGACY_DEFAULT_PORT}{DEFAULT_PATH}"
SCHEME_PORT_DEFAULTS = {"http": 80, "https": 443}


def _validate_server(server: str) -> None:
    """Validate server string. Raises ValueError on invalid input."""
    if not server or not server.strip():
        raise ValueError("Server address cannot be empty.")

    server = server.strip()
    has_scheme = server.startswith(("http://", "https://"))

    if not has_scheme:
        # Check if it has some other scheme (e.g., mqtt://, ftp://)
        if "://" in server:
            scheme = server.split("://")[0]
            raise ValueError(f"Invalid server '{server}': scheme must be http or https, got '{scheme}'")
        server = f"http://{server}"

    parsed = urlparse(server)

    if not parsed.hostname:
        raise ValueError(f"Invalid server '{server}': could not determine host")
    if " " in parsed.hostname:
        raise ValueError(f"Invalid host '{parsed.hostname}': must not contain spaces")

    try:
        port = parsed.port
    except ValueError as e:
        if "out of range" in str(e):
            raise ValueError(f"Invalid server '{server}': port must be between 1 and 65535")
        raise ValueError(f"Invalid server '{server}': port is not a valid integer")

    if port is not None and (port < 1 or port > 65535):
        raise ValueError(f"Invalid server '{server}': port must be between 1 and 65535, got {port}")


def _normalize_server_url(server: str, exact_path: bool = False) -> str:
    """Validate and normalize server string to a full URL.
    
    Args:
        server: User-provided server URL string.
        exact_path: If True, preserve the user-provided path exactly (including '/').
                    If False (default), treat empty or root path as '/api'.
    """
    _validate_server(server)

    server = server.strip()
    is_bare = not server.startswith(("http://", "https://"))
    if is_bare:
        server = f"http://{server}"

    parsed = urlparse(server)

    # Determine port
    explicit_port = parsed.port
    if explicit_port is not None:
        port = explicit_port
    elif is_bare:
        port = LEGACY_DEFAULT_PORT
    else:
        port = SCHEME_PORT_DEFAULTS.get(parsed.scheme, 80)

    # Build netloc: omit port only if it matches the scheme's standard default
    scheme_default = SCHEME_PORT_DEFAULTS.get(parsed.scheme)
    if not is_bare and port == scheme_default:
        netloc = parsed.hostname
    else:
        netloc = f"{parsed.hostname}:{port}"

    # Determine path
    if exact_path:
        path = parsed.path
    else:
        path = parsed.path if parsed.path and parsed.path not in ("/", "") else DEFAULT_PATH

    return urlunparse(parsed._replace(netloc=netloc, path=path))


def get_config_dir() -> Path:
    override = os.environ.get("LOGSEQ_CLI_CONFIG_DIR")
    if override:
        return Path(override)

    system = platform.system()
    home = Path.home()

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "logseq-cli"
        return home / "AppData" / "Roaming" / "logseq-cli"

    if system == "Darwin":
        return home / "Library" / "Application Support" / "logseq-cli"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "logseq-cli"
    return home / ".config" / "logseq-cli"


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_config(config: dict[str, Any]) -> Path:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def set_token(token: str) -> str:
    token = token.strip()
    config = load_config()
    config["token"] = token
    save_config(config)
    return token


def get_token() -> str | None:
    token = load_config().get("token")
    return token if isinstance(token, str) and token else None


def resolve_token() -> str | None:
    """Resolve the current token. Priority: LOGSEQ_TOKEN env var > config file."""
    token = os.environ.get("LOGSEQ_TOKEN")
    if token:
        return token
    return get_token()


def set_server(server: str, exact_path: bool = False) -> str:
    _validate_server(server)
    normalized = _normalize_server_url(server, exact_path=exact_path)
    config = load_config()
    config["server"] = normalized
    save_config(config)
    return normalized


def load_config_file_server() -> str | None:
    """Load server from config file. Returns None if not configured."""
    config = load_config()
    server = config.get("server")
    if isinstance(server, str) and server:
        return server
    return None


def resolve_server(default: str = DEFAULT_SERVER) -> str:
    """Resolve the current server to a full URL string.

    Priority: LOGSEQ_SERVER env var > config file > default.

    Env var values are normalized at resolution time. Config file values are
    trusted as-is (they are normalized at write time by `set_server`).
    """
    env_server = os.environ.get("LOGSEQ_SERVER")

    if env_server:
        server_str = env_server.strip()
        try:
            return _normalize_server_url(server_str)
        except ValueError as e:
            raise ValueError(f"Invalid server from LOGSEQ_SERVER '{server_str}': {e}")

    server_str = load_config_file_server()
    if server_str:
        return server_str.strip()

    return default
