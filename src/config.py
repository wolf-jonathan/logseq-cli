from __future__ import annotations

import json
import os
import platform
import re
from pathlib import Path
from typing import Any


def _validate_host_value(host: str) -> None:
    """Validate host at the config layer. Raises ValueError for invalid hosts."""
    if not host or not host.strip():
        raise ValueError("Host cannot be empty.")
    if re.search(r"[\s\x00-\x1f]", host):
        raise ValueError(f"Invalid host '{host}': must not contain spaces or control characters.")


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


def set_token(token: str) -> Path:
    config = load_config()
    config["token"] = token
    return save_config(config)


def get_token() -> str | None:
    token = load_config().get("token")
    return token if isinstance(token, str) and token else None


def set_host(host: str) -> Path:
    _validate_host_value(host)
    config = load_config()
    config["host"] = host
    return save_config(config)


def get_host() -> str:
    config = load_config()
    host = config.get("host")
    return host if isinstance(host, str) and host else "127.0.0.1"


def set_port(port: int) -> Path:
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError(f"Port must be between 1 and 65535, got {port}")
    config = load_config()
    config["port"] = port
    return save_config(config)


def get_port() -> int:
    config = load_config()
    port = config.get("port")
    if isinstance(port, int) and 1 <= port <= 65535:
        return port
    return 12315
