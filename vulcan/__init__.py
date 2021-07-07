import warnings
from dataclasses import asdict, dataclass
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
class Metadata:
    name: Optional[str]
    version: Optional[str]

    description: Optional[str] = None
    long_description: Optional[str] = None

    author: Optional[str] = None
    author_email: Optional[str] = None

    maintainer: Optional[str] = None
    maintainer_email: Optional[str] = None

    url: Optional[str] = None
    download_url: Optional[str] = None

    py_modules: Optional[List[str]] = None
    scripts: Optional[str] = None

    classifiers: Optional[List[str]] = None
    license: Optional[str] = None
    keywords: Optional[List[str]] = None
    platforms: Optional[str] = None

    packages: Optional[List[str]] = None
    package_dir: Optional[Dict[str, str]] = None

    install_requires: Optional[List[str]] = None
    extras_require: Optional[Dict[str, List[str]]] = None
    python_requires: Optional[str] = None

    entry_points: Optional[Dict[str, List[str]]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


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
    source_path: Path
    plugins: Optional[List[str]]
    metadata: Metadata
    shiv_options: List[ShivOpts]
    lockfile: Path
    configured_dependencies: VersionSpecs
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
        install_requires, extras_require = None, None
        if not no_lock:
            install_requires, extras_require = get_requires(lockfile)

        metadata = Metadata(
            name=str_or_none(config.get('name')),
            version=str_or_none(version),
            description=str_or_none(config.get("description")),
            long_description=Path(source_path / config.get("readme")
                                  ).read_text() if config.get("readme") is not None else None,
            author=str_or_none(config.get("author")),
            author_email=str_or_none(config.get("author_email")),
            maintainer=str_or_none(config.get("maintainer")),
            maintainer_email=config.get("maintainer_email"),
            url=str_or_none(config.get("url")),
            download_url=str_or_none(config.get("download_url")),
            py_modules=list_or_none(config.get("py_modules")),
            scripts=str_or_none(config.get("scripts")),
            classifiers=list_or_none(config.get("classifiers")),
            license=str_or_none(config.get("license")),
            keywords=list_or_none(config.get("keywords")),
            platforms=str_or_none(config.get("platforms")),
            packages=list_or_none(config.get("packages")),
            package_dir=dict_or_none(config.get("package_dir")),
            extras_require=extras_require,
            python_requires=str_or_none(config.get("python_requires")),
            install_requires=install_requires,
            entry_points={section: [f'{k}={v}' for k, v in section_vals.items()]
                          for section, section_vals in config.get('entry_points', {}).items()} or None
            )

        python_lock_with = config.get('python-lock-with')

        shiv_ops = []
        shiv_config = config.get('shiv', [])
        for conf in shiv_config:
            shiv_ops.append(ShivOpts(
                bin_name=str(conf.get('bin_name', metadata.name)),
                console_script=str_or_none(conf.get('console_script')),
                entry_point=str_or_none(conf.get('entry_point')),
                interpreter=str_or_none(conf.get('interpreter')),
                with_extras=[str(e) for e in conf.get('with_extras', [])],
                extra_args=str(conf.get('extra_args', '')),
            ))

        return cls(source_path=source_path, plugins=list_or_none(config.get('plugins')),
                   metadata=metadata, lockfile=lockfile, shiv_options=shiv_ops,
                   configured_dependencies=config.get('dependencies', {}),
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
        # e.g. "options_sdk", "~=1.2.3" -> "options_sdk~=1.2.3"
        return f'{lib}{req}'
    try:
        extras = f'[{",".join(req["extras"])}]' if 'extras' in req else ''
        # "options_sdk", {"version": "~=1.2.3", "extras"=["networkx","git"]}
        #                           -> "options_sdk[networkx,git]~=1.2.3"
        # "options_sdk", {"version": "~=1.2.3"} -> "options_sdk~=1.2.3"
        return f'{lib}{extras}{req["version"]}'
    except KeyError as e:
        raise VulcanConfigError(f'invalid requirement {lib} ({req}) -- {e}') from e
