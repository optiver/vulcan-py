from pathlib import Path
from unittest.mock import Mock

import pytest

from vulcan import Vulcan, VulcanConfigError
from vulcan.plugins import PluginRunner


def _runner(source: Path, plugin_list: str, tables: str) -> PluginRunner:
    (source / "pyproject.toml").write_text(
        '[project]\nname = "testproject"\n'
        '[tool.vulcan]\nno-lock = true\n'
        f'plugins = {plugin_list}\n{tables}'
    )
    return PluginRunner(Vulcan.from_source(source))


@pytest.mark.parametrize(
    ("plugin_list", "tables", "installed_name"),
    [
        ('["missing"]', "", "missing"),
        ('["configured", "missing"]', "[tool.vulcan.plugin.configured]\n", "configured"),
    ],
)
def test_missing_config_stops_before_loading_plugins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plugin_list: str, tables: str, installed_name: str
) -> None:
    runner = _runner(tmp_path, plugin_list, tables)
    entrypoint = Mock()
    entrypoint.name = installed_name
    monkeypatch.setattr(runner, "get_pre_entrypoints", lambda: [entrypoint])

    with pytest.raises(VulcanConfigError, match="missing"):
        with runner:
            pytest.fail("build should not start without plugin configuration")

    entrypoint.load.assert_not_called()


def test_explicitly_empty_plugin_config_is_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner(tmp_path, '["configured"]', "[tool.vulcan.plugin.configured]\n")
    entrypoint = Mock()
    entrypoint.name = "configured"
    monkeypatch.setattr(runner, "get_pre_entrypoints", lambda: [entrypoint])

    with runner:
        entrypoint.load.return_value.assert_called_once_with({})
