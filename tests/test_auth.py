import json


def test_auth_set_token_stores_token(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-token", "token-1234"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "token-1234"


def test_auth_set_token_overwrites_existing_token(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_token
    from src.cli.main import app

    set_token("old-token")
    result = runner.invoke(app, ["auth", "set-token", "new-token"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "new-token"


def test_auth_set_token_prompts_when_token_argument_omitted(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-token"], input="prompt-token\n")

    assert result.exit_code == 0
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["token"] == "prompt-token"


def test_auth_status_reports_missing_token(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert f"Config path: {tmp_path / 'config.json'}" in result.stdout
    assert "Stored token: missing" in result.stdout
    assert "Run `logseq auth set-token` to store a token." in result.stdout


def test_auth_status_masks_stored_token(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_token
    from src.cli.main import app

    set_token("token-1234")
    result = runner.invoke(app, ["auth", "status"])

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


def test_auth_set_port_rejects_zero(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-port", "0"])

    assert result.exit_code == 2
    assert "Port must be between 1 and 65535" in result.output


def test_auth_set_port_rejects_negative(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    # Negative numbers require '--' separator to avoid being parsed as CLI options
    result = runner.invoke(app, ["auth", "set-port", "--", "-1"])

    assert result.exit_code == 2
    assert "Port must be between 1 and 65535" in result.output


def test_auth_set_port_rejects_non_integer(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-port", "abc"])

    assert result.exit_code == 2
    assert "not a valid integer" in result.output


def test_auth_set_port_rejects_too_large(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-port", "65536"])

    assert result.exit_code == 2
    assert "Port must be between 1 and 65535" in result.output


def test_auth_set_port_accepts_valid_port(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-port", "8080"])

    assert result.exit_code == 0
    assert "Stored Logseq port: 8080" in result.stdout


def test_auth_set_port_accepts_boundary_ports(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result_1 = runner.invoke(app, ["auth", "set-port", "1"])
    assert result_1.exit_code == 0

    result_65535 = runner.invoke(app, ["auth", "set-port", "65535"])
    assert result_65535.exit_code == 0


def test_config_set_port_rejects_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_port

    import pytest
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        set_port(0)


def test_config_set_port_rejects_negative(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_port

    import pytest
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        set_port(-1)


def test_config_set_port_rejects_too_large(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_port

    import pytest
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        set_port(65536)


def test_config_get_port_falls_back_for_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import save_config, get_port

    save_config({"port": 0})
    assert get_port() == 12315


def test_config_get_port_falls_back_for_negative(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import save_config, get_port

    save_config({"port": -1})
    assert get_port() == 12315


def test_config_get_port_falls_back_for_too_large(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import save_config, get_port

    save_config({"port": 70000})
    assert get_port() == 12315


def test_auth_set_host_rejects_empty(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-host", ""])

    assert result.exit_code == 2
    assert "Host cannot be empty" in result.output


def test_auth_set_host_rejects_whitespace(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-host", "  "])

    assert result.exit_code == 2
    assert "Host cannot be empty" in result.output


def test_auth_set_host_rejects_spaces(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-host", "my host"])

    assert result.exit_code == 2
    assert "must not contain spaces" in result.output


def test_auth_set_host_accepts_valid_host(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-host", "10.191.64.81"])

    assert result.exit_code == 0
    assert "Stored Logseq host: 10.191.64.81" in result.stdout


def test_auth_set_host_accepts_localhost(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.cli.main import app

    result = runner.invoke(app, ["auth", "set-host", "127.0.0.1"])

    assert result.exit_code == 0


def test_config_set_host_rejects_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_host

    import pytest
    with pytest.raises(ValueError, match="Host cannot be empty"):
        set_host("")


def test_config_set_host_rejects_spaces(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_host

    import pytest
    with pytest.raises(ValueError, match="must not contain spaces"):
        set_host("my host")


def test_config_set_host_accepts_valid(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))

    from src.config import set_host, get_host

    set_host("10.0.0.1")
    assert get_host() == "10.0.0.1"
