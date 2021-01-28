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

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Vulcan:
    metadata: Metadata

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
            patforms=config.get("patforms"),
            packages=config.get("packages"),
            )
        setuptools_options = dict(
            install_requires=get_requires(source_path / config.get('lockfile', 'vulcan.lock'))
            )
        options = {**distutils_options, **setuptools_options}
        return cls(metadata=Metadata(**options))


def get_requires(lockfile: Path) -> List[str]:
    if not lockfile.exists():
        return []
    return lockfile.read_text().strip().split('\n')
