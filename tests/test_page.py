import json
import pytest
from typer.testing import CliRunner
from unittest.mock import AsyncMock, patch
from src.cli.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_service():
    with patch("src.cli.main.get_service") as mock:
        svc = AsyncMock()
        mock.return_value = svc
        yield svc


# --- page list ---

def test_page_list_returns_ndjson(runner, mock_service):
    mock_service.get_all_pages_raw.return_value = [
        {"originalName": "Page A", "uuid": "1", "journal?": False, "properties": {}},
        {"originalName": "Page B", "uuid": "2", "journal?": True, "properties": {}},
    ]
    result = runner.invoke(app, ["page", "list"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["name"] == "Page A"
    assert json.loads(lines[1])["name"] == "Page B"


def test_page_list_handles_pages_without_uuid(runner, mock_service):
    mock_service.get_all_pages_raw.return_value = [
        {"originalName": "Page A", "journal?": False, "properties": {}},
    ]
    result = runner.invoke(app, ["page", "list"])
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip()) == {
        "name": "Page A",
        "uuid": None,
        "properties": {},
        "isJournal": False,
    }


def test_page_list_handles_pages_without_original_name(runner, mock_service):
    mock_service.get_all_pages_raw.return_value = [
        {"id": 10050, "name": "project/truedcexit", "createdAt": 1776070218475},
    ]
    result = runner.invoke(app, ["page", "list"])
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip()) == {
        "name": "project/truedcexit",
        "uuid": None,
        "properties": None,
        "isJournal": None,
    }


def test_page_list_fields_option(runner, mock_service):
    mock_service.get_all_pages_raw.return_value = [
        {"originalName": "Page A", "uuid": "1", "journal?": False, "properties": {}},
    ]
    result = runner.invoke(app, ["page", "list", "--fields", "name"])
    assert result.exit_code == 0
    obj = json.loads(result.stdout.strip())
    assert "name" in obj
    assert "uuid" not in obj


def test_page_list_plain_option(runner, mock_service):
    mock_service.get_all_pages_raw.return_value = [
        {"originalName": "שלום", "uuid": "1", "journal?": False, "properties": {}},
    ]
    result = runner.invoke(app, ["page", "list", "--plain"])
    assert result.exit_code == 0
    assert "שלום" in result.stdout
    assert result.stdout.strip()[0] != "{"  # Not JSON


def test_page_list_defaults_to_all_pages(runner, mock_service):
    """Default should return all pages, not paginated."""
    mock_service.get_all_pages_raw.return_value = [
        {"originalName": f"Page {i}", "uuid": str(i), "journal?": False, "properties": {}}
        for i in range(120)
    ]
    result = runner.invoke(app, ["page", "list"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 120


def test_page_list_page_and_page_size_options(runner, mock_service):
    mock_service.get_all_pages.return_value = {
        "pages": [{"name": "Page A", "uuid": "1", "isJournal": False}],
        "total": 100,
    }
    result = runner.invoke(app, ["page", "list", "--page", "2", "--page-size", "10"])
    assert result.exit_code == 0
    mock_service.get_all_pages.assert_called_with(page_number=2, page_size=10)


# --- page get ---

def test_page_get_returns_page_ndjson(runner, mock_service):
    mock_service.get_page_by_name.return_value = {"name": "My Page", "uuid": "abc"}
    result = runner.invoke(app, ["page", "get", "My Page"])
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip())["name"] == "My Page"


def test_page_get_not_found_exits_1(runner, mock_service):
    mock_service.get_page_by_name.return_value = None
    result = runner.invoke(app, ["page", "get", "Missing"])
    assert result.exit_code == 1


def test_page_get_reads_name_from_stdin(runner, mock_service):
    mock_service.get_page_by_name.return_value = {"name": "Page A", "uuid": "1"}
    stdin = json.dumps({"name": "Page A"}) + "\n"
    result = runner.invoke(app, ["page", "get"], input=stdin)
    assert result.exit_code == 0
    mock_service.get_page_by_name.assert_called_with("Page A")


# --- page create ---

def test_page_create_prints_created_page(runner, mock_service):
    mock_service.create_page.return_value = {"name": "New Page", "uuid": "xyz"}
    result = runner.invoke(app, ["page", "create", "New Page"])
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip())["name"] == "New Page"


# --- page delete ---

def test_page_delete_exits_0(runner, mock_service):
    mock_service.delete_page.return_value = None
    result = runner.invoke(app, ["page", "delete", "Old Page"])
    assert result.exit_code == 0
    mock_service.delete_page.assert_called_with("Old Page")


def test_page_delete_reads_name_from_stdin(runner, mock_service):
    mock_service.delete_page.return_value = None
    stdin = json.dumps({"name": "Old Page"}) + "\n"
    result = runner.invoke(app, ["page", "delete"], input=stdin)
    assert result.exit_code == 0
    mock_service.delete_page.assert_called_with("Old Page")


# --- page rename ---

def test_page_rename_calls_rename_page(runner, mock_service):
    mock_service.rename_page.return_value = None
    result = runner.invoke(app, ["page", "rename", "Old", "New"])
    assert result.exit_code == 0
    mock_service.rename_page.assert_called_with("Old", "New")


# --- page refs ---

def test_page_refs_returns_ndjson(runner, mock_service):
    mock_service.get_page_linked_references.return_value = [
        {"name": "Ref A"}, {"name": "Ref B"}
    ]
    result = runner.invoke(app, ["page", "refs", "My Page"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2


# --- page properties ---

def test_page_properties_returns_ndjson(runner, mock_service):
    mock_service.get_page_properties.return_value = {"type": "note", "tags": "python"}
    result = runner.invoke(app, ["page", "properties", "My Page"])
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip())["type"] == "note"
    mock_service.get_page_properties.assert_called_with("My Page")


# --- page journal ---

def test_page_journal_creates_page(runner, mock_service):
    mock_service.create_journal_page.return_value = {"name": "01.01.2030", "uuid": "j1", "isJournal": True}
    result = runner.invoke(app, ["page", "journal", "2030-01-01"])
    assert result.exit_code == 0
    mock_service.create_journal_page.assert_called_with("2030-01-01")
    assert json.loads(result.stdout.strip())["name"] == "01.01.2030"


def test_page_journal_invalid_date_exits_1(runner, mock_service):
    mock_service.create_journal_page.side_effect = ValueError("time data 'bad-date' does not match format '%Y-%m-%d'")
    result = runner.invoke(app, ["page", "journal", "bad-date"])
    assert result.exit_code == 1
    assert "Error:" in result.stderr


# --- page ns-list ---

def test_page_ns_list_returns_ndjson(runner, mock_service):
    mock_service.get_pages_from_namespace.return_value = [
        {"originalName": "Projects/Alpha", "uuid": "1"},
        {"originalName": "Projects/Beta", "uuid": "2"},
    ]
    result = runner.invoke(app, ["page", "ns-list", "Projects"])
    assert result.exit_code == 0
    mock_service.get_pages_from_namespace.assert_called_with("Projects")
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2


# --- page ns-tree ---

def test_page_ns_tree_returns_ndjson(runner, mock_service):
    mock_service.get_pages_tree_from_namespace.return_value = [
        {"name": "Projects", "children": [{"name": "Projects/Alpha"}]}
    ]
    result = runner.invoke(app, ["page", "ns-tree", "Projects"])
    assert result.exit_code == 0
    mock_service.get_pages_tree_from_namespace.assert_called_with("Projects")


# --- help text coverage ---

def test_page_list_has_help(runner):
    result = runner.invoke(app, ["page", "list", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout
    assert "--plain" in result.stdout
    assert "--page" in result.stdout
    assert "name, uuid" in result.stdout


def test_page_get_has_help(runner):
    result = runner.invoke(app, ["page", "get", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout
    assert "--plain" in result.stdout


def test_page_create_has_help(runner):
    result = runner.invoke(app, ["page", "create", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout


def test_page_delete_has_help(runner):
    result = runner.invoke(app, ["page", "delete", "--help"])
    assert result.exit_code == 0
    assert "piped" in result.stdout.lower() or "NDJSON" in result.stdout


def test_page_rename_has_help(runner):
    result = runner.invoke(app, ["page", "rename", "--help"])
    assert result.exit_code == 0
    assert "SRC" in result.stdout or "src" in result.stdout.lower()
    assert "DEST" in result.stdout or "dest" in result.stdout.lower()


def test_page_refs_has_help(runner):
    result = runner.invoke(app, ["page", "refs", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout
    assert "--plain" in result.stdout


def test_page_properties_has_help(runner):
    result = runner.invoke(app, ["page", "properties", "--help"])
    assert result.exit_code == 0
    assert "--plain" in result.stdout


def test_page_journal_has_help(runner):
    result = runner.invoke(app, ["page", "journal", "--help"])
    assert result.exit_code == 0
    assert "YYYY-MM-DD" in result.stdout


def test_page_ns_list_has_help(runner):
    result = runner.invoke(app, ["page", "ns-list", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout
    assert "namespace" in result.stdout.lower() or "NAMESPACE" in result.stdout


def test_page_ns_tree_has_help(runner):
    result = runner.invoke(app, ["page", "ns-tree", "--help"])
    assert result.exit_code == 0
    assert "--plain" in result.stdout
