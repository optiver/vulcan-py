import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List

from vulcan import Vulcan, to_pep508

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
    options = config.metadata.asdict()
    if config_settings and config_settings.get('no-lock') == 'true':
        options['install_requires'] = [to_pep508(lib, req)
                                       for lib, req in config.configured_dependencies.items()]
        options['extras_require'] = config.configured_extras

    with patch_argv(['bdist_wheel']):
        # https://setuptools.readthedocs.io/en/latest/userguide/keywords.html
        # https://docs.python.org/3/distutils/apiref.html
        dist = setup(**options, include_package_data=True)
        rel_dist = Path(dist.dist_files[0][-1])
        rel_dist.rename(Path(wheel_directory) / rel_dist.name)
        return rel_dist.name


def build_sdist(sdist_directory: str,
                config_settings: Dict[str, str] = None,
                ) -> str:
    config = Vulcan.from_source(Path().absolute())
    options = config.metadata.asdict()
    if config_settings and config_settings.get('no-lock'):
        options['install_requires'] = [to_pep508(lib, req)
                                       for lib, req in config.configured_dependencies.items()]
        options['extras_require'] = config.configured_extras
    with patch_argv(['sdist']):
        dist = setup(**options, include_package_data=True)
        rel_dist = Path(dist.dist_files[0][-1])
        rel_dist.rename(Path(sdist_directory) / rel_dist.name)
        return rel_dist.name


# not part of PEP-517, but very useful to have
def install_develop() -> None:
    config = Vulcan.from_source(Path().absolute())
    options = config.metadata.asdict()
    virtual_env = os.environ.get('VIRTUAL_ENV')
    if virtual_env is None:
        exit('may not use vulcan develop outside of a virtualenv')

    setup = Path('setup.py')
    if setup.exists():
        exit('may not use vulcan develop when setup.py is present')
    try:
        with tempfile.NamedTemporaryFile(suffix='.json', mode="w+") as mdata_file:
            mdata_file.write(json.dumps(options))
            mdata_file.flush()
            with setup.open('w+') as setup_file:
                setup_file.write(f"""\
from setuptools import setup
import json, pathlib
setup(**json.load(pathlib.Path('{mdata_file.name}').open()))
""")
            subprocess.check_call([
                Path(virtual_env, 'bin', 'python'), '-m', 'pip', 'install', '-e', Path().absolute()])
    finally:
        setup.unlink()


# tox requires these two fro some reason :(
def get_requires_for_build_sdist(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def get_requires_for_build_wheel(config_settings: Dict[str, str] = None) -> List[str]:
    return []
