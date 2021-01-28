from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml


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
    patforms: Optional[str] = None

    packages: Optional[List[str]] = None

    install_requires: Optional[List[str]] = None

    entry_points: Optional[Dict[str, List[str]]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShivOpts:
    bin_name: str
    console_script: Optional[str] = None
    entry_point: Optional[str] = None
    interpreter: Optional[str] = None
    extra_args: str = ''


@dataclass
class Vulcan:
    metadata: Metadata
    shiv_options: ShivOpts
    lockfile: Path
    configured_dependencies: List[str]

    @classmethod
    def from_source(cls, source_path: Path) -> 'Vulcan':
        with open(source_path / 'pyproject.toml') as f:
            config = toml.load(f)['tool']['vulcan']
        distutils_options = dict(
            name=config["name"],
            version=config["version"],
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
            )
        setuptools_options = dict(
            install_requires=get_requires(source_path / config.get('lockfile', 'vulcan.lock')),
            entry_points={section: [f'{k}={v}' for k, v in section_vals.items()]
                          for section, section_vals in config.get('entry_points', {}).items()}
            )
        options = {**distutils_options, **setuptools_options}

        metadata = Metadata(**options)

        lockfile = source_path / config.get('lockfile', 'vulcan.lock')
        configured_deps = config.get('dependencies', {})

        shiv_config = config.get('shiv', {})
        shiv_opts = ShivOpts(
            bin_name=shiv_config.get('bin_name', metadata.name),
            console_script=shiv_config.get('console_script'),
            entry_point=shiv_config.get('entry_point'),
            interpreter=shiv_config.get('interpreter'),
            extra_args=shiv_config.get('extra_args', ''),
        )

        return cls(metadata=metadata, lockfile=lockfile, shiv_options=shiv_opts,
                   configured_dependencies=configured_deps)


def get_requires(lockfile: Path) -> List[str]:
    if not lockfile.exists():
        return []
    return [line for line in lockfile.read_text().strip().split('\n') if line]
