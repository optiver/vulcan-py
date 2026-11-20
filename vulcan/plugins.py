from __future__ import annotations
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Dict, Iterable, Type, Optional
from pathlib import Path

import tomlkit
from pkg_resources import EntryPoint, iter_entry_points

from vulcan import Vulcan, VulcanConfigError


@dataclass
class PluginRunner:
    vulcan: Vulcan
    plugin_configs: Dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        try:
            pyproject = self.vulcan.source_path / "pyproject.toml"
            self.plugin_configs = tomlkit.loads(pyproject.read_text())["tool"]["vulcan"]["plugin"]  # type: ignore
        except KeyError:
            self.plugin_configs = {}

    def get_pre_entrypoints(self) -> Iterable[EntryPoint]:
        return iter_entry_points("vulcan.pre_build")

    def get_post_entrypoints(self) -> Iterable[EntryPoint]:
        return iter_entry_points("vulcan.post_build")

    def __enter__(self) -> "PluginRunner":
        enabled_plugins = self.vulcan.plugins
        if not enabled_plugins:
            return self
        for name in enabled_plugins:
            if name not in self.plugin_configs:
                raise VulcanConfigError(
                    f"Missing configuration for Vulcan plugin {name!r}: "
                    "add an entry under [tool.vulcan.plugin] in pyproject.toml."
                )
        for ep in self.get_pre_entrypoints():
            if ep.name not in enabled_plugins:
                continue
            print(f"Running pre_build plugin {ep}")
            ep.load()(self.plugin_configs[ep.name])
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        tb: TracebackType | None = None,
    ) -> None:
        if exc_type is not None:
            # if the build process raises an error, don't bother with the plugins.
            return None
        # NOT implementing post_build plugins yet, until I see a motivating example
        return None


def test_plugin(config: Optional[Dict[str, str]]) -> None:
    assert config is not None
    assert config["foobar"] == "barfoo"
    (Path(config["module_dir"]) / "example.no-hash.py").write_text("Text!")
