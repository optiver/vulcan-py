import configparser
import os
from pathlib import Path
from typing import List, Optional

from vulcan.metadata import build_metadata
from vulcan.options import (build_entry_points, build_package_data,
                            build_packages, check_unsupported)

# importing setuptools here rather than at point of use forces user to specify setuptools in their
# [build-system][requires] section
try:
    from setuptools.build_meta import _BuildMetaBackend  # type: ignore
except ImportError as e:
    raise ImportError(str(e) + '\nPlease add setuptools to [build-system] requires in pyproject.toml') from e

__all__ = ['get_requires_for_build_sdist',
           'get_requires_for_build_wheel',
           'prepare_metadata_for_build_wheel',
           'build_wheel',
           'build_sdist']


def gen_setup_cfg() -> None:
    # importing here rather than at top level because toml is not built-in
    import toml
    check_required_files()
    config = configparser.ConfigParser(interpolation=None)
    # here we read it in, even if we don't expect it to be there, because we only support basic param
    # generation from pyproject.toml so if someone wants to do something more interesting they will still need
    # to have both files
    config.read('setup.cfg')  # fine even if the file doesn't exist

    # guarenteed to be here by the check_required_files above
    pyproject = toml.load('pyproject.toml')

    version_file = find_version_file()
    if version_file is not None:
        with version_file.open() as version_f:
            build_version = version_f.read().strip()
            pyproject['tool']['poetry']['version'] = build_version

    # all of these modify config in-place
    build_metadata(config, pyproject)
    build_packages(config, pyproject)
    build_package_data(config, pyproject)
    build_entry_points(config, pyproject)
    check_unsupported(config, pyproject)

    with open('setup.cfg', 'w+') as f:
        config.write(f)

    with open('setup.cfg') as f:
        # purely for debug purposes, pip will hide the output of this if -v is not provided
        print("Generated setup.cfg:")
        print(f.read())


def find_version_file() -> Optional[Path]:
    try:
        return next(Path().rglob('VERSION'))
    except StopIteration:
        return None


def check_required_files() -> None:
    for f in ('pyproject.toml', 'poetry.lock'):
        if not os.path.exists(f):
            raise RuntimeError(f"No {f} found in {os.getcwd()}. This file is required")


# For docs on the hooks: https://www.python.org/dev/peps/pep-0517/#build-backend-interface
class ApplicationBuildMetaBackend(_BuildMetaBackend):  # type: ignore

    def run_setup(self, setup_script: str = 'setup.py') -> str:
        _old_setup = None
        if os.path.exists('setup.cfg'):
            print("Existant setup.cfg found, saving to recreate after generated setup is complete")
            # we need to do this because tox does not correctly change working directory when building, which
            # means the generated setup.cfg when run under tox ends up in the toxinidir. See:
            # https://github.com/tox-dev/tox/blob/master/src/tox/helper/build_isolated.py

            # This is NOT true for pip, which correctly creates a working directory in /tmp
            with open('setup.cfg') as f:
                _old_setup = f.read()
        # generate setup.cfg from pyproject.toml
        try:
            gen_setup_cfg()
            # run setup
            return str(super().run_setup(setup_script))
        finally:
            # remove/undo any generated configs in setup.cfg (so we're back to clean
            # checkout if we're under tox)
            if _old_setup is not None:
                print("Recreating old setup.cfg")
                with open('setup.cfg', 'w+') as f:
                    f.write(_old_setup)
            else:
                print("Removing generated setup.cfg")
                os.remove('setup.cfg')

    def build_sdist(self, sdist_directory: str, config_settings: str = None) -> str:
        # just here to show that they are here
        return str(super().build_sdist(sdist_directory, config_settings))

    def build_wheel(self, wheel_directory: str, config_settings: str = None, metadata_directory: str = None
                    ) -> str:
        # just here to show that they are here
        return str(super().build_wheel(wheel_directory, config_settings, metadata_directory))

    def prepare_metadata_for_build_wheel(self, metadata_directory: str, config_settings: str = None) -> str:
        # just here to show that they are here
        return str(super().prepare_metadata_for_build_wheel(metadata_directory, config_settings))

    def get_requires_for_build_wheel(self, config_settings: str = None) -> List[str]:
        return ['setuptools', 'wheel >= 0.25', 'poetry', 'toml']

    def get_requires_for_build_sdist(self, config_settings: str = None) -> List[str]:
        return ['setuptools', 'poetry', 'toml']


# The primary backend
_BACKEND = ApplicationBuildMetaBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
