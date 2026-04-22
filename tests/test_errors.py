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


# ---- LOGSEQ_SERVER env var tests ----

def test_env_server_bare_hostname_works(runner, monkeypatch, tmp_path):
    """Bare hostname without port uses default port 12315."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_TOKEN", "test-token")
    monkeypatch.setenv("LOGSEQ_SERVER", "127.0.0.1")
    from unittest.mock import patch
    with patch("src.cli.main._check_connectivity") as mock_check:
        result = runner.invoke(app, ["graph", "info"])
    # Called with default port since no port specified
    mock_check.assert_called_once_with("127.0.0.1", 12315)


def test_env_server_full_url_works(runner, monkeypatch, tmp_path):
    """Full URL with scheme and port is parsed correctly."""
    monkeypatch.setenv("LOGSEQ_CLI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("LOGSEQ_TOKEN", "test-token")
    monkeypatch.setenv("LOGSEQ_SERVER", "http://10.0.0.1:8080")
    from unittest.mock import patch
    with patch("src.cli.main._check_connectivity") as mock_check:
        result = runner.invoke(app, ["graph", "info"])
    mock_check.assert_called_once_with("10.0.0.1", 8080)


def test_env_server_non_integer_port_exits_1_with_friendly_message(runner):
    """LOGSEQ_SERVER with non-integer port is rejected."""
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_SERVER": "127.0.0.1:abc"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_SERVER"] = "127.0.0.1:abc"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "not a valid integer" in result.stderr


def test_env_server_port_out_of_range_exits_1_with_friendly_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_SERVER": "127.0.0.1:0"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_SERVER"] = "127.0.0.1:0"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "port must be between 1 and 65535" in result.stderr


def test_env_server_host_with_spaces_exits_1_with_friendly_message(runner):
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_SERVER": "my host:12315"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_SERVER"] = "my host:12315"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "must not contain spaces" in result.stderr


def test_connectivity_check_fails_with_friendly_message(runner):
    """When Logseq is not running, get_service should print a clear connectivity error."""
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_SERVER": "127.0.0.1:1"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_SERVER"] = "127.0.0.1:1"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "Cannot connect to Logseq" in result.stderr


def test_connectivity_error_shows_host_and_port(runner):
    """Connectivity error message should include the configured host and port."""
    with patch.dict("os.environ", {"LOGSEQ_CLI_CONFIG_DIR": "tmp-test-config", "LOGSEQ_TOKEN": "test-token", "LOGSEQ_SERVER": "127.0.0.1:1"}, clear=True):
        import os
        os.environ["LOGSEQ_TOKEN"] = "test-token"
        os.environ["LOGSEQ_SERVER"] = "127.0.0.1:1"
        result = runner.invoke(app, ["graph", "info"])
    assert result.exit_code == 1
    assert "127.0.0.1:1" in result.stderr


# ---- get_current_graph integration test ----

def test_get_current_graph_returns_graph_info(monkeypatch, tmp_path):
    """When Logseq returns graph info, it should be parsed correctly."""
    import httpx
    from src.cli.auth import _get_current_graph

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"name": "工作活动", "path": "D:/Document/Sync/SynologyDrive/AppData/logseq/工作活动", "url": "logseq_local_D:/Document/Sync/SynologyDrive/AppData/logseq/工作活动"}
        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            return FakeResponse()

    import unittest.mock
    with unittest.mock.patch("httpx.Client", FakeClient):
        result = _get_current_graph("127.0.0.1", 12315, "fake-token")

    assert result is not None
    assert result["name"] == "工作活动"
    assert "工作活动" in result["path"]


def test_get_current_graph_returns_none_on_error(monkeypatch, tmp_path):
    """When Logseq API errors, _get_current_graph should return None."""
    import httpx
    from src.cli.auth import _get_current_graph

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            raise httpx.RequestError("Connection refused")

    import unittest.mock
    with unittest.mock.patch("httpx.Client", FakeClient):
        result = _get_current_graph("127.0.0.1", 12315, "fake-token")

    assert result is None
