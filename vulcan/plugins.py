from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Dict, Type

import tomlkit
from pkg_resources import iter_entry_points

from vulcan import Vulcan


@dataclass
class PluginRunner:
    vulcan: Vulcan
    plugin_configs: Dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        try:
            pyproject = self.vulcan.source_path / 'pyproject.toml'
            self.plugin_configs = tomlkit.loads(pyproject.read_text()  # type: ignore
                                                )['tool']['vulcan']['plugin']
        except KeyError:
            self.plugin_configs = {}

    def __enter__(self) -> 'PluginRunner':

        for ep in iter_entry_points('vulcan.pre_build'):
            print(f"Running pre_build plugin {ep}")
            ep.load()(self.plugin_configs.get(ep.name))
        return self

    def __exit__(self,
                 exc_type: Type[BaseException] = None,
                 exc_value: BaseException = None,
                 tb: TracebackType = None) -> None:
        if exc_type is not None:
            # if the build process raises an error, don't bother with the plugins.
            return None
        # NOT implementing post_build plugins yet, until I see a motivating example
        return None
