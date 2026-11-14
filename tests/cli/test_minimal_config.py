from pathlib import Path
from unittest.mock import Mock

import pytest
import tomlkit
from click.testing import CliRunner

from vulcan import Vulcan, cli

pytestmark = pytest.mark.cli


@pytest.mark.parametrize("other_tool", ["", "\n[tool.setuptools]\n"])
def test_read_project_without_vulcan_table(tmp_path: Path, other_tool: str) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "testproject"\n' + other_tool)
    config = Vulcan.from_source(tmp_path, fail_on_missing_lock=False)
    assert config.configured_dependencies == {}
    assert config.lockfile == tmp_path / "vulcan.lock"


@pytest.mark.parametrize(
    "existing, expected",
    [("", ["dependencies"]), ('dynamic = ["version"]\n', ["version", "dependencies"])],
)
def test_add_bootstraps_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: str, expected: list[str]
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "testproject"\n' + existing)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "get_virtualenv_python", lambda: Path("unused-python"))
    install = Mock()
    monkeypatch.setattr(cli.subprocess, "check_call", install)

    result = CliRunner().invoke(cli.main, ["add", "--no-lock", "textual==1.0"])
    assert result.exit_code == 0, result.exception
    updated = tomlkit.parse(pyproject.read_text())
    assert updated["project"]["dynamic"] == expected  # type: ignore[index]
    assert Vulcan.from_source(tmp_path, fail_on_missing_lock=False).configured_dependencies == {"textual": "==1.0"}
    assert install.call_count == 1


def test_add_does_not_modify_static_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject = tmp_path / "pyproject.toml"
    original = '[project]\nname = "testproject"\ndependencies = ["requests"]\n'
    pyproject.write_text(original)
    monkeypatch.chdir(tmp_path)
    install = Mock()
    monkeypatch.setattr(cli.subprocess, "check_call", install)

    result = CliRunner().invoke(cli.main, ["add", "--no-lock", "textual==1.0"])
    assert result.exit_code == 2
    assert "Declare project.dependencies as dynamic" in result.output
    assert pyproject.read_text() == original
    install.assert_not_called()
