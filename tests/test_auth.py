import json

from typer.testing import CliRunner


def runner():
    return CliRunner()


def test_auth_set_token_stores_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner().invoke(app, ["auth", "set-token", "token-1234"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "token-1234"


def test_auth_set_token_overwrites_existing_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_token
    from src.cli.main import app

    set_token("old-token")
    result = runner().invoke(app, ["auth", "set-token", "new-token"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "new-token"


def test_auth_set_token_prompts_when_token_argument_omitted(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner().invoke(app, ["auth", "set-token"], input="prompt-token\n")

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "prompt-token"


def test_auth_status_reports_missing_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.auth import app

    result = runner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert f"Config path: {tmp_path / 'config.json'}" in result.stdout
    assert "Stored token: missing" in result.stdout
    assert "Run `logseq auth set-token` to store a token." in result.stdout


def test_auth_status_masks_stored_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_token
    from src.cli.auth import app

    set_token("token-1234")
    result = runner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert f"Config path: {tmp_path / 'config.json'}" in result.stdout
    assert "Stored token: ******1234" in result.stdout


def test_get_service_uses_stored_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("LOGSEQ_TOKEN", raising=False)

    from src.config import set_token
    from src.cli.main import get_service

    set_token("stored-token")
    service = get_service(check_connectivity=False)

    assert service._client._headers["Authorization"] == "Bearer stored-token"


def test_env_token_overrides_stored_token(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_TOKEN", "env-token")

    from src.config import set_token
    from src.cli.main import get_service

    set_token("stored-token")
    service = get_service(check_connectivity=False)

    assert service._client._headers["Authorization"] == "Bearer env-token"


# ---- set-server tests ----

def test_auth_set_server_rejects_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", ""])
    assert result.exit_code == 2
    assert "cannot be empty" in result.output


def test_auth_set_server_accepts_bare_hostname_no_port(monkeypatch, tmp_path):
    """Bare hostname without port is valid (uses default port 12315)."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=True):
        result = runner().invoke(app, ["auth", "set-server", "127.0.0.1"])
    assert result.exit_code == 0
    assert "Stored Logseq server: 127.0.0.1" in result.stdout


def test_auth_set_server_rejects_port_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", "127.0.0.1:0"])
    assert result.exit_code == 2
    assert "between" in result.output and "65535" in result.output


def test_auth_set_server_rejects_port_too_large(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", "127.0.0.1:65536"])
    assert result.exit_code == 2
    assert "between" in result.output and "65535" in result.output


def test_auth_set_server_rejects_non_integer_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", "127.0.0.1:abc"])
    assert result.exit_code == 2
    assert "valid integer" in result.output


def test_auth_set_server_rejects_host_with_spaces(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", "my host:12315"])
    assert result.exit_code == 2
    assert "must not contain spaces" in result.output


def test_auth_set_server_accepts_valid(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=True):
        result = runner().invoke(app, ["auth", "set-server", "http://10.191.64.81:12315"])
    assert result.exit_code == 0
    assert "Stored Logseq server: http://10.191.64.81:12315" in result.stdout
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["server"] == "http://10.191.64.81:12315"
    assert "host" not in config
    assert "port" not in config


def test_auth_set_server_accepts_boundary_ports(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=True):
        r1 = runner().invoke(app, ["auth", "set-server", "http://127.0.0.1:1"])
        assert r1.exit_code == 0
        r2 = runner().invoke(app, ["auth", "set-server", "http://127.0.0.1:65535"])
        assert r2.exit_code == 0


# ---- config layer tests ----

def test_config_set_server_rejects_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import set_server
    import pytest
    for val in ["", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1:abc", "my host:12315"]:
        with pytest.raises(ValueError):
            set_server(val)


def test_config_set_server_cleans_legacy_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import set_server, load_config, save_config
    save_config({"host": "old", "port": 9999, "token": "tok"})
    set_server("http://10.0.0.1:8080")
    config = load_config()
    assert config["server"] == "http://10.0.0.1:8080"
    assert config["token"] == "tok"


def test_config_get_server_backward_compat(monkeypatch, tmp_path):
    """get_server() returns None for legacy host/port keys - CLI handles default."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import get_server, save_config
    save_config({"host": "10.0.0.1", "port": 8080})
    assert get_server() is None


def test_config_get_server_defaults(monkeypatch, tmp_path):
    """get_server() returns None when no config exists - CLI handles default."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import get_server
    assert get_server() is None


def test_config_get_server_uses_new_key(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import save_config, get_server
    save_config({"server": "http://192.168.1.1:9999"})
    assert get_server() == "http://192.168.1.1:9999"


def test_config_resolve_server_env_overrides_config(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_SERVER", "http://10.0.0.2:5555")
    from src.config import save_config, resolve_server
    save_config({"server": "http://127.0.0.1:12315"})
    url = resolve_server(default="http://fallback:12315")
    assert url == "http://10.0.0.2:5555"


def test_config_resolve_server_env_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_SERVER", "127.0.0.1:abc")
    from src.config import resolve_server
    import pytest
    with pytest.raises(ValueError, match="port is not a valid integer"):
        resolve_server(default="http://fallback:12315")

def test_config_resolve_server_invalid_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_SERVER", "mqtt://127.0.0.1:1883")
    from src.config import resolve_server
    import pytest
    with pytest.raises(ValueError, match="scheme must be http or https"):
        resolve_server(default="http://fallback:12315")

# ---- set-server connectivity prompt tests ----

def test_auth_set_server_prompts_on_connection_failure_and_aborts_on_n(monkeypatch, tmp_path):
    """When connection fails, user declines save (default N)."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=False):
        result = runner().invoke(app, ["auth", "set-server", "127.0.0.1:12315"], input="n\n")
    assert result.exit_code == 0
    assert "Cannot connect to Logseq" in result.output
    assert "not saved" in result.output
    assert not (tmp_path / "config.json").exists()


def test_auth_set_server_prompts_on_connection_failure_and_saves_on_y(monkeypatch, tmp_path):
    """When connection fails, user confirms save (Y)."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=False):
        result = runner().invoke(app, ["auth", "set-server", "127.0.0.1:12315"], input="y\n")
    assert result.exit_code == 0
    assert "Stored Logseq server: 127.0.0.1:12315" in result.stdout
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["server"] == "127.0.0.1:12315"


def test_auth_set_server_saves_immediately_when_connected(monkeypatch, tmp_path):
    """When connection succeeds, save happens without prompt."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_TOKEN", "test-token")
    from src.cli.main import app
    from unittest.mock import patch

    with patch("src.cli.auth._check_connectivity", return_value=True):
        with patch("src.cli.auth.get_token", return_value="test-token"):
            with patch("src.cli.auth._get_current_graph", return_value={"name": "Test Graph", "path": "/tmp/test"}):
                result = runner().invoke(app, ["auth", "set-server", "http://127.0.0.1:12315"], input="y\n")

    assert result.exit_code == 0
    assert "Stored Logseq server: http://127.0.0.1:12315" in result.stdout
    assert "Connection: OK" in result.stdout
    assert "Current Graph:" in result.stdout
    assert "Test Graph" in result.stdout
    assert "Is this the correct graph?" in result.stdout
    assert "Save this server address anyway" not in result.output
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["server"] == "http://127.0.0.1:12315"


# ---- URL normalizing tests ----

def test_normalize_server_full_url_preserves_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("http://10.191.64.81:12315") == "http://10.191.64.81:12315"


def test_normalize_server_http_url_omits_default_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("http://example.com") == "http://example.com"


def test_normalize_server_https_url_omits_default_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("https://example.com") == "https://example.com"


def test_normalize_server_https_with_explicit_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("https://example.com:8443") == "https://example.com:8443"


def test_normalize_server_bare_hostname_adds_scheme_and_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("10.191.64.81") == "http://10.191.64.81:12315"


def test_normalize_server_trailing_colon_adds_default_port(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    assert _normalize_server_url("10.191.64.81:") == "http://10.191.64.81:12315"


def test_normalize_server_empty_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    import pytest
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_server_url("")


def test_normalize_server_invalid_schema_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import _normalize_server_url
    import pytest
    with pytest.raises(ValueError, match="scheme must be http or https"):
        _normalize_server_url("mqtt://127.0.0.1:1883")


def test_auth_set_server_accepts_full_url(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch

    with patch("src.cli.auth._check_connectivity", return_value=True):
        result = runner().invoke(app, ["auth", "set-server", "http://example.com:8080"])

    assert result.exit_code == 0
    assert "Stored Logseq server: http://example.com:8080" in result.stdout
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["server"] == "http://example.com:8080"


def test_auth_set_server_accepts_https(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch

    with patch("src.cli.auth._check_connectivity", return_value=True):
        result = runner().invoke(app, ["auth", "set-server", "https://example.com"])

    assert result.exit_code == 0
    assert "Stored Logseq server: https://example.com" in result.stdout


def test_config_get_server_defaults_still_returns_none(monkeypatch, tmp_path):
    """get_server() returns None when no config exists - CLI provides default."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import get_server
    assert get_server() is None


def test_config_resolve_server_bare_hostname_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_SERVER", "10.0.0.1")
    from src.config import resolve_server
    url = resolve_server(default="http://fallback:12315")
    assert url == "http://10.0.0.1:12315"


def test_config_resolve_server_uses_default_when_nothing_configured(monkeypatch, tmp_path):
    """resolve_server uses default when no env var or config exists."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.config import resolve_server
    url = resolve_server(default="http://my-default:9999")
    assert url == "http://my-default:9999"


def test_auth_set_server_shows_graph_info_warning_when_unavailable(monkeypatch, tmp_path):
    """When graph info cannot be retrieved, show a warning."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_TOKEN", "test-token")
    from src.cli.main import app
    from unittest.mock import patch

    with patch("src.cli.auth._check_connectivity", return_value=True):
        with patch("src.cli.auth.get_token", return_value="test-token"):
            with patch("src.cli.auth._get_current_graph", return_value=None):
                result = runner().invoke(app, ["auth", "set-server", "http://127.0.0.1:12315"])

    assert result.exit_code == 0
    assert "Stored Logseq server: http://127.0.0.1:12315" in result.stdout
    assert "Connection: OK" in result.stdout
    assert "Could not retrieve current graph info" in result.stdout


# ---- trim tests ----

def test_auth_set_server_trims_whitespace(monkeypatch, tmp_path):
    """Leading/trailing whitespace should be trimmed from server address."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    from unittest.mock import patch
    with patch("src.cli.auth._check_connectivity", return_value=True):
        result = runner().invoke(app, ["auth", "set-server", "  http://example.com:8080  "])
    assert result.exit_code == 0
    assert "Stored Logseq server: http://example.com:8080" in result.stdout
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["server"] == "http://example.com:8080"


def test_auth_set_server_rejects_whitespace_only(monkeypatch, tmp_path):
    """Whitespace-only input should be rejected as empty."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-server", "   "])
    assert result.exit_code == 2
    assert "cannot be empty" in result.output


def test_auth_set_token_trims_whitespace(monkeypatch, tmp_path):
    """Leading/trailing whitespace should be trimmed from token."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    from src.cli.main import app
    result = runner().invoke(app, ["auth", "set-token", "  my-token  "])
    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "my-token"

