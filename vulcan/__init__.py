from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
import warnings

import toml


def find_version_file(source_dir: Path) -> Optional[Path]:
    try:
        return next(source_dir.rglob('VERSION'))
    except StopIteration:
        return None


@dataclass
class Metadata:
    name: str
    version: str

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


@dataclass
class Vulcan:
    metadata: Metadata
    shiv_options: List[ShivOpts]
    lockfile: Path
    configured_dependencies: Dict[str, Union[str, Dict[str, str]]]
    configured_extras: Dict[str, List[str]]

    @classmethod
    def from_source(cls, source_path: Path) -> 'Vulcan':
        with open(source_path / 'pyproject.toml') as f:
            config = toml.load(f)['tool']['vulcan']
        version_file = find_version_file(source_path)
        version = version_file.read_text().strip() if version_file is not None else config.get('version')
        lockfile = source_path / config.get('lockfile', 'vulcan.lock')

        install_requires, extras_require = get_requires(lockfile)

        distutils_options = dict(
            name=config["name"],
            version=version,
            description=config.get("description"),
            long_description=Path(source_path / config.get("readme")
                                  ).read_text() if config.get("readme") is not None else None,
            author=config.get("author"),
            author_email=config.get("author_email"),
            maintainer=config.get("maintainer"),
            maintainer_email=config.get("maintainer_email"),
            url=config.get("url"),
            download_url=config.get("download_url"),
            py_modules=config.get("py_modules"),
            scripts=config.get("scripts"),
            classifiers=config.get("classifiers"),
            license=config.get("license"),
            keywords=config.get("keywords"),
            platforms=config.get("platforms"),
            packages=config.get("packages"),
            package_dir=config.get("package_dir"),
            extras_require=extras_require,
            python_requires=config.get("python_requires")
            )
        setuptools_options = dict(
            install_requires=install_requires,
            entry_points={section: [f'{k}={v}' for k, v in section_vals.items()]
                          for section, section_vals in config.get('entry_points', {}).items()}
            )
        options = {**distutils_options, **setuptools_options}

        metadata = Metadata(**options)

        configured_deps = config.get('dependencies', {})

        shiv_ops = []
        shiv_config = config.get('shiv', [])
        for conf in shiv_config:
            shiv_ops.append(ShivOpts(
                bin_name=conf.get('bin_name', metadata.name),
                console_script=conf.get('console_script'),
                entry_point=conf.get('entry_point'),
                interpreter=conf.get('interpreter'),
                with_extras=conf.get('with_extras', []),
                extra_args=conf.get('extra_args', ''),
            ))

        return cls(metadata=metadata, lockfile=lockfile, shiv_options=shiv_ops,
                   configured_dependencies=configured_deps, configured_extras=config.get('extras', {}))


def get_requires(lockfile: Path) -> Tuple[List[str], Dict[str, List[str]]]:
    if not lockfile.exists():
        warnings.warn(f"No lockfile {lockfile} found")
        return [], {}
    with lockfile.open() as f:
        content = toml.load(f)
    return content['install_requires'], content['extras_require']
