import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List

from vulcan import Vulcan

# importing setuptools here rather than at point of use forces user to specify setuptools in their
# [build-system][requires] section
try:
    from setuptools import setup  # type: ignore
except ImportError as e:
    raise ImportError(str(e) + '\nPlease add setuptools to [build-system] requires in pyproject.toml') from e

__all__ = ['build_wheel',
           'build_sdist']


@contextmanager
def patch_argv(argv: List[str]) -> Generator[None, None, None]:
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + argv
    yield
    sys.argv = old_argv


def build_wheel(wheel_directory: str, config_settings: Dict[str, str] = None,
                metadata_directory: str = None) -> str:
    config = Vulcan.from_source(Path().absolute())
    with patch_argv(['bdist_wheel']):
        # https://setuptools.readthedocs.io/en/latest/userguide/keywords.html
        # https://docs.python.org/3/distutils/apiref.html
        dist = setup(**config.metadata.asdict(),
                     include_package_data=True)
        rel_dist = Path(dist.dist_files[0][-1])
        rel_dist.rename(Path(wheel_directory) / rel_dist.name)
        return rel_dist.name


def build_sdist(sdist_directory: str,
                config_settings: Dict[str, str] = None,
                ) -> str:
    config = Vulcan.from_source(Path().absolute())
    with patch_argv(['sdist']):
        dist = setup(**config.metadata.asdict(),
                     include_package_data=True)
        rel_dist = Path(dist.dist_files[0][-1])
        rel_dist.rename(Path(sdist_directory) / rel_dist.name)
        return rel_dist.name


# not part of PEP-517, but very useful to have
def install_develop(setuptools_args: List[str] = None) -> None:
    config = Vulcan.from_source(Path().absolute())
    extra_args = ['--index-url', 'http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple']
    if setuptools_args:
        extra_args.extend(setuptools_args)
    with patch_argv(['develop'] + extra_args):
        setup(**config.metadata.asdict(),
              include_package_data=True)


# tox requires these two fro some reason :(
def get_requires_for_build_sdist(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def get_requires_for_build_wheel(config_settings: Dict[str, str] = None) -> List[str]:
    return []
