import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union, cast

import tomlkit
from typing_extensions import TypedDict


def find_version_file(source_dir: Path) -> Optional[Path]:
    try:
        return next(source_dir.rglob('VERSION'))
    except StopIteration:
        return None


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


class _ContainerStub(tomlkit.container.Container):
    def get(self, v: str, default: Any = None) -> Any:
        ...


def list_or_none(val: Any) -> Optional[List[str]]:
    return [str(v) for v in val] if val is not None else None


def str_or_none(val: Any) -> Optional[str]:
    return str(val) if val is not None else None


def dict_or_none(val: Any) -> Optional[Dict[str, Any]]:
    return {str(k): v for k, v in val.items()} if val is not None else None


@dataclass
class Vulcan:
    version: Optional[str]
    packages: Optional[List[str]]
    source_path: Path
    plugins: Optional[List[str]]
    shiv_options: List[ShivOpts]
    lockfile: Path
    dependencies: List[str]
    configured_dependencies: VersionSpecs
    extras: Dict[str, List[str]]
    configured_extras: Dict[str, List[str]]
    no_lock: bool = False
    python_lock_with: Optional[str] = None

    @classmethod
    def from_source(cls, source_path: Path) -> 'Vulcan':
        with open(source_path / 'pyproject.toml') as f:
            config = tomlkit.loads(f.read())['tool']['vulcan']  # type: ignore
            config = cast(_ContainerStub, config)
        version_file = find_version_file(source_path)
        version = version_file.read_text().strip() if version_file is not None else config.get('version')
        lockfile = source_path / config.get('lockfile', 'vulcan.lock')

        no_lock = config.get('no-lock', False)
        install_requires: List[str] = []
        extras_require: Dict[str, List[str]] = {}
        if not no_lock:
            install_requires, extras_require = get_requires(lockfile)

        python_lock_with = config.get('python-lock-with')

        shiv_ops = []
        shiv_config = config.get('shiv', [])
        for conf in shiv_config:
            shiv_ops.append(ShivOpts(
                bin_name=str(conf.get('bin_name')),
                console_script=str_or_none(conf.get('console_script')),
                entry_point=str_or_none(conf.get('entry_point')),
                interpreter=str_or_none(conf.get('interpreter')),
                with_extras=[str(e) for e in conf.get('with_extras', [])],
                extra_args=str(conf.get('extra_args', '')),
            ))

        print(f"Setting version to {version}")
        return cls(version=version, source_path=source_path, plugins=list_or_none(config.get('plugins')),
                   packages=list_or_none(config.get("packages")),
                   lockfile=lockfile, shiv_options=shiv_ops,
                   dependencies=install_requires,
                   configured_dependencies=config.get('dependencies', {}),
                   extras=extras_require,
                   configured_extras=config.get('extras', {}),
                   no_lock=no_lock, python_lock_with=python_lock_with)


def get_requires(lockfile: Path) -> Tuple[List[str], Dict[str, List[str]]]:
    if not lockfile.exists():
        warnings.warn(f"No lockfile {lockfile} found")
        return [], {}
    with lockfile.open() as f:
        content = cast(_ContainerStub, tomlkit.loads(f.read()))
    return (list(content['install_requires']),  # type: ignore
            {k: list(v) for k, v in content['extras_require'].items()})  # type: ignore


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
