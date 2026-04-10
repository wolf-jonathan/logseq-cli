import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.main import app
from src.cli import skill as skill_module


@pytest.fixture
def runner():
    from typer.testing import CliRunner

    return CliRunner()


def test_skill_install_creates_all_default_targets(runner, tmp_path):
    home = tmp_path / "home"
    mock_source_content = "---\nname: logseq-cli\n---\n# Test"

    with (
        patch.object(skill_module, "get_skill_source_content", return_value=mock_source_content),
        patch.object(skill_module.Path, "home", return_value=home),
    ):
        result = runner.invoke(app, ["skill", "install"])

    assert result.exit_code == 0
    assert "installed" in result.stdout.lower()
    assert (home / ".claude" / "skills" / "logseq-cli" / "SKILL.md").exists()
    assert (home / ".agents" / "skills" / "logseq-cli" / "SKILL.md").exists()


def test_skill_install_project_agents_target_only(runner, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    mock_source_content = "---\nname: logseq-cli\n---\n# Test"

    with (
        patch.object(skill_module, "get_skill_source_content", return_value=mock_source_content),
        patch.object(skill_module.Path, "home", return_value=home),
        patch.object(skill_module.Path, "cwd", return_value=project),
    ):
        result = runner.invoke(app, ["skill", "install", "--scope", "project", "--target", "agents"])

    assert result.exit_code == 0
    assert (project / ".agents" / "skills" / "logseq-cli" / "SKILL.md").exists()
    assert not (project / ".claude" / "skills" / "logseq-cli" / "SKILL.md").exists()


def test_skill_install_source_not_found(runner):
    with patch.object(skill_module, "get_skill_source_content", return_value=None):
        result = runner.invoke(app, ["skill", "install"])

    assert result.exit_code == 1
    assert "not found" in result.stderr.lower()


def test_skill_install_partial_failure_reports_both(runner, tmp_path):
    home = tmp_path / "home"
    mock_source_content = "---\nname: logseq-cli\n---\n# Test"

    claude_dir = home / ".claude" / "skills" / "logseq-cli"
    claude_dir.parent.mkdir(parents=True)
    claude_dir.write_text("blocker")

    with (
        patch.object(skill_module, "get_skill_source_content", return_value=mock_source_content),
        patch.object(skill_module.Path, "home", return_value=home),
    ):
        result = runner.invoke(app, ["skill", "install"])

    assert result.exit_code == 1
    assert "failed" in result.stderr.lower()
    assert (home / ".agents" / "skills" / "logseq-cli" / "SKILL.md").exists()


def test_skill_status_not_installed(runner, tmp_path):
    home = tmp_path / "home"

    with patch.object(skill_module.Path, "home", return_value=home):
        result = runner.invoke(app, ["skill", "status"])

    assert result.exit_code == 0
    assert "not installed" in result.stdout.lower()
    assert "claude code" in result.stdout.lower()
    assert "agent skills" in result.stdout.lower()


def test_skill_status_version_mismatch(runner, tmp_path):
    home = tmp_path / "home"
    skill_dest = home / ".agents" / "skills" / "logseq-cli" / "SKILL.md"
    skill_dest.parent.mkdir(parents=True)
    skill_dest.write_text("<!-- logseq-cli v0.0.1 -->\n# Test")

    with patch.object(skill_module.Path, "home", return_value=home):
        result = runner.invoke(app, ["skill", "status"])

    assert result.exit_code == 0
    assert "version mismatch" in result.stdout.lower()


def test_skill_uninstall_removes_selected_target_only(runner, tmp_path):
    home = tmp_path / "home"
    skill_dest = home / ".agents" / "skills" / "logseq-cli" / "SKILL.md"
    other_dest = home / ".claude" / "skills" / "logseq-cli" / "SKILL.md"
    skill_dest.parent.mkdir(parents=True)
    skill_dest.write_text("# Test")
    other_dest.parent.mkdir(parents=True)
    other_dest.write_text("# Test")

    with patch.object(skill_module.Path, "home", return_value=home):
        result = runner.invoke(app, ["skill", "uninstall", "--target", "agents"])

    assert result.exit_code == 0
    assert not skill_dest.exists()
    assert other_dest.exists()


def test_skill_show_displays_source_content(runner):
    with patch.object(
        skill_module,
        "get_skill_source_content",
        return_value="# Logseq CLI Skill\nTest content",
    ):
        result = runner.invoke(app, ["skill", "show"])

    assert result.exit_code == 0
    assert "Logseq CLI Skill" in result.stdout


def test_skill_show_installed_target(runner, tmp_path):
    home = tmp_path / "home"
    skill_dest = home / ".claude" / "skills" / "logseq-cli" / "SKILL.md"
    skill_dest.parent.mkdir(parents=True)
    skill_dest.write_text("# Logseq CLI Skill\nInstalled content")

    with patch.object(skill_module.Path, "home", return_value=home):
        result = runner.invoke(app, ["skill", "show", "--target", "claude"])

    assert result.exit_code == 0
    assert "Installed content" in result.stdout


def test_wheel_includes_root_skill_content(tmp_path):
    if shutil.which("uv") is None:
        pytest.skip("uv is required for build smoke tests")

    repo_root = Path(__file__).resolve().parents[1]
    build_dir = tmp_path / "dist"
    env = dict(os.environ, UV_CACHE_DIR=str(tmp_path / "uv-cache"))
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(build_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "failed to fetch" in stderr or "connect error" in stderr or "os error 10013" in stderr:
            pytest.skip("uv build requires network access to resolve build dependencies")
        assert result.returncode == 0, result.stderr

    wheel_path = next(build_dir.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        packaged_skill = wheel.read("src/data/SKILL.md").decode("utf-8")

    assert packaged_skill == (repo_root / "SKILL.md").read_text(encoding="utf-8")


def test_sdist_includes_root_skill_file(tmp_path):
    if shutil.which("uv") is None:
        pytest.skip("uv is required for build smoke tests")

    repo_root = Path(__file__).resolve().parents[1]
    build_dir = tmp_path / "dist"
    env = dict(os.environ, UV_CACHE_DIR=str(tmp_path / "uv-cache"))
    result = subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(build_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "failed to fetch" in stderr or "connect error" in stderr or "os error 10013" in stderr:
            pytest.skip("uv build requires network access to resolve build dependencies")
        assert result.returncode == 0, result.stderr

    sdist_path = next(build_dir.glob("*.tar.gz"))
    with tarfile.open(sdist_path, "r:gz") as sdist:
        names = sdist.getnames()

    assert any(name.endswith("/SKILL.md") for name in names)


def test_sync_packaged_skill_accepts_packaged_fallback(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    setup_path = repo_root / "setup.py"
    setup_source = setup_path.read_text(encoding="utf-8")
    namespace: dict[str, object] = {"__file__": str(setup_path)}

    with patch("setuptools.setup"):
        exec(compile(setup_source, str(setup_path), "exec"), namespace)

    packaged_skill = tmp_path / "src" / "data" / "SKILL.md"
    packaged_skill.parent.mkdir(parents=True)
    packaged_skill.write_text("# Packaged skill", encoding="utf-8")

    namespace["ROOT_SKILL"] = tmp_path / "SKILL.md"
    namespace["PACKAGED_SKILL"] = packaged_skill

    namespace["sync_packaged_skill"]()

    assert packaged_skill.read_text(encoding="utf-8") == "# Packaged skill"
