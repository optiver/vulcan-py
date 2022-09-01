import distutils.core
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union, cast

import tomlkit
import tomlkit.container
import tomlkit.items
from setuptools import setup
from typing_extensions import TypedDict


class VulcanConfigError(Exception):
    pass


class VersionDict(TypedDict, total=False):
    version: str
    extras: List[str]


VersionSpecs = Mapping[str, Union[str, VersionDict]]


def flatten_reqs(versions: VersionSpecs) -> List[str]:
    return [to_pep508(lib, req) for lib, req in versions.items()]


@dataclass
class ShivOpts:
    bin_name: str
    console_script: Optional[str] = None
    entry_point: Optional[str] = None
    interpreter: Optional[str] = None
    with_extras: Optional[List[str]] = None
    extra_args: str = ''


def list_or_none(val: Any) -> Optional[List[str]]:
    return [str(v) for v in val] if val is not None else None


def str_or_none(val: Any) -> Optional[str]:
    return str(val) if val is not None else None


def dict_or_none(val: Any) -> Optional[Dict[str, Any]]:
    return {str(k): v for k, v in val.items()} if val is not None else None


@dataclass
class Vulcan:
    source_path: Path
    plugins: Optional[List[str]]
    shiv_options: List[ShivOpts]
    lockfile: Path
    dependencies: Optional[List[str]]
    configured_dependencies: VersionSpecs
    extras: Optional[Dict[str, List[str]]]
    configured_extras: Dict[str, List[str]]
    dev_dependencies: Dict[str, VersionSpecs]
    dynamic: Optional[List[str]]
    no_lock: bool = False
    python_lock_with: Optional[str] = None

    @classmethod
    def from_source(cls, source_path: Path, fail_on_missing_lock: bool = True) -> 'Vulcan':
        with open(source_path / 'pyproject.toml') as f:
            all_config = tomlkit.loads(f.read())
            config = all_config['tool']['vulcan']  # type: ignore[index]
            assert isinstance(config, dict)
            dynamic = all_config['project'].get('dynamic', [])  # type: ignore[union-attr]
        lockfile = source_path / config.get('lockfile', 'vulcan.lock')

        no_lock = config.get('no-lock', False)
        install_requires: Optional[List[str]] = []
        extras_require: Optional[Dict[str, List[str]]] = {}
        if not no_lock:
            try:
                install_requires, extras_require = get_requires(lockfile)
            except FileNotFoundError:
                if fail_on_missing_lock:
                    raise
                install_requires = None
                extras_require = None

        python_lock_with = config.get('python-lock-with')

        shiv_ops = []
        shiv_config = config.get('shiv', [])
        for conf in shiv_config:
            shiv_ops.append(
                ShivOpts(
                    bin_name=str(conf.get('bin_name')),
                    console_script=str_or_none(conf.get('console_script')),
                    entry_point=str_or_none(conf.get('entry_point')),
                    interpreter=str_or_none(conf.get('interpreter')),
                    with_extras=[str(e) for e in conf.get('with_extras', [])],
                    extra_args=str(conf.get('extra_args', '')),
                ))
        # note that setuptools also checks this, and says that it _should_ consider this a warning, but will
        # not for the intermediate period.
        # We'll consider it an error until setuptools sees fit to do it for us, and then remove this check.
        if 'dependencies' in config and 'dependencies' not in dynamic:
            raise RuntimeError("tool.vulcan.dependencies configured but 'dependencies' not in dynamic,"
                               " this is an error according to PEP-621. "
                               "See https://peps.python.org/pep-0621/#dynamic for more information")
        if 'extras' in config and 'optional-dependencies' not in dynamic:
            raise RuntimeError("tool.vulcan.extras configured but 'optional-dependencies' not in dynamic,"
                               " this is an error according to PEP-621. "
                               "See https://peps.python.org/pep-0621/#dynamic for more information")

        return cls(source_path=source_path,
                   plugins=list_or_none(config.get('plugins')),
                   lockfile=lockfile,
                   shiv_options=shiv_ops,
                   dependencies=install_requires,
                   configured_dependencies=config.get('dependencies', {}),
                   extras=extras_require,
                   dev_dependencies=config.get('dev-dependencies', {}),
                   configured_extras=config.get('extras', {}),
                   no_lock=no_lock,
                   python_lock_with=python_lock_with,
                   dynamic=dynamic)

    def setup(self, config_settings: Dict[str, str] = None) -> distutils.core.Distribution:
        install_requires: Optional[List[str]]
        extras_require: Optional[Dict[str, List[str]]]
        if self.no_lock or (config_settings and config_settings.get('no-lock') == 'true'):
            install_requires = flatten_reqs(self.configured_dependencies)
            extras_require = self.configured_extras
        else:
            install_requires = self.dependencies
            extras_require = self.extras
        # setuptools apparently does not know what setuptools returns
        # very reassuring
        return setup(  # type: ignore[no-any-return,func-returns-value]
            install_requires=install_requires,
            extras_require=extras_require)


def get_requires(lockfile: Path) -> Tuple[List[str], Dict[str, List[str]]]:
    if not lockfile.exists():
        raise FileNotFoundError(f"Expected lockfile {lockfile}, does not exist")
    with lockfile.open() as f:
        content = cast(tomlkit.container.Container, tomlkit.loads(f.read()))
    return (
        list(content['install_requires']),  # type: ignore
        {k: list(v)
         for k, v in content['extras_require'].items()})  # type: ignore


def to_pep508(lib: str, req: Union[str, VersionDict]) -> str:
    if not isinstance(req, (str, dict)):
        raise VulcanConfigError(f"Invalid requirement {req} -- must be a dict or a string")
    if isinstance(req, str):
        # e.g. "example_lib", "~=1.2.3" -> "example_lib~=1.2.3"
        return f'{lib}{req}'
    try:
        extras = f'[{",".join(req["extras"])}]' if 'extras' in req else ''
        # "example_lib", {"version": "~=1.2.3", "extras"=["networkx","git"]}
        #                           -> "example_lib[networkx,git]~=1.2.3"
        # "example_lib", {"version": "~=1.2.3"} -> "example_lib~=1.2.3"
        return f'{lib}{extras}{req["version"]}'
    except KeyError as e:
        raise VulcanConfigError(f'invalid requirement {lib} ({req}) -- {e}') from e
