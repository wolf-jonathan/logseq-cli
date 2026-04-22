import json
import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


def test_missing_token_exits_1_with_clear_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config"}, clear=True):
        # Ensure LOGSEQ_TOKEN is not set
        import os
        os.environ.pop("LOGSEQ_TOKEN", None)
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "logseq auth set-token" in result.stderr


def test_connect_error_prints_friendly_message(runner):
    with patch("src.cli.main.get_service") as mock:
        svc = AsyncMock()
        svc.get_current_graph.side_effect = httpx.ConnectError("refused")
        mock.return_value = svc
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "Cannot connect to Logseq" in result.stderr


def test_http_status_error_shows_status_code(runner):
    with patch("src.cli.main.get_service") as mock:
        svc = AsyncMock()
        response = MagicMock()
        response.status_code = 401
        svc.get_current_graph.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=response
        )
        mock.return_value = svc
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "401" in result.stderr


def test_error_goes_to_stderr_stdout_stays_clean(runner):
    with patch("src.cli.main.get_service") as mock:
        svc = AsyncMock()
        svc.get_current_graph.side_effect = httpx.ConnectError("refused")
        mock.return_value = svc
        result = runner.invoke(app, ["graph", "info"])
    assert result.stdout == ""
    assert result.exit_code == 1


def test_missing_required_arg_exits_nonzero(runner):
    with patch("src.cli.main.get_service") as mock:
        mock.return_value = AsyncMock()
        result = runner.invoke(app, ["block", "update"])
    assert result.exit_code != 0


def test_env_port_non_integer_exits_1_with_friendly_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_PORT": "abc"}, clear=True):
        import os
        os.environ.pop("LOGSEQ_TOKEN", None)
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_PORT"] = "abc"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "LOGSEQ_PORT must be a valid integer" in result.stderr


def test_env_port_out_of_range_exits_1_with_friendly_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_PORT": "-1"}, clear=True):
        import os
        os.environ.pop("LOGSEQ_TOKEN", None)
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_PORT"] = "-1"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "LOGSEQ_PORT must be between 1 and 65535" in result.stderr


def test_env_host_empty_is_rejected_with_friendly_message(runner):
    """Empty LOGSEQ_HOST env var is rejected with a clear error (not silently falling back)."""
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_HOST": ""}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_HOST"] = ""
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "LOGSEQ_HOST cannot be empty" in result.stderr


def test_env_host_with_spaces_exits_1_with_friendly_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_HOST": "my host"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_HOST"] = "my host"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "must not contain spaces" in result.stderr


def test_connectivity_check_fails_with_friendly_message(runner):
    """When Logseq is not running, get_service should print a clear connectivity error."""
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_HOST": "127.0.0.1", "LOGSEQ_PORT": "1"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_HOST"] = "127.0.0.1"
        os.environ["LOGSEQ_PORT"] = "1"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "Cannot connect to Logseq" in result.stderr


def test_connectivity_error_shows_host_and_port(runner):
    """Connectivity error message should include the configured host and port."""
    # Use a port that is guaranteed to refuse connection instantly (no timeout)
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_HOST": "127.0.0.1", "LOGSEQ_PORT": "1"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_HOST"] = "127.0.0.1"
        os.environ["LOGSEQ_PORT"] = "1"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    # Port 1 will refuse, so we get connect error with host:port
    assert "127.0.0.1:1" in result.stderr
