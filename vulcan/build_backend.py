import configparser
import os
import subprocess
from collections import defaultdict
from typing import Any, Dict, List, Mapping

# importing setuptools here rather than at point of use forces user to specify setuptools in their
# [build-system][requires] section
try:
    import pkg_resources
    import pkg_resources.extern  # type: ignore
    from setuptools.build_meta import _BuildMetaBackend  # type: ignore
except ImportError as e:
    raise ImportError(str(e) + '\nPlease add setuptools to [build-system] requires in pyproject.toml') from e

__all__ = ['get_requires_for_build_sdist',
           'get_requires_for_build_wheel',
           'prepare_metadata_for_build_wheel',
           'build_wheel',
           'build_sdist']


def build_packages(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    if not config.has_section('options'):
        config['options'] = {}
    config['options']['install_requires'] = '\n'.join([str(req) for req in gen_reqs()])
    find = False
    if 'packages' not in config['options']:
        find = True
        config['options']['packages'] = 'find:'

    if 'packages' in pyproject['tool']['poetry'] and find:
        config['options.packages.find'] = convert_packages(pyproject['tool']['poetry']['packages'])

    if 'python' in pyproject['tool']['poetry'].get('dependencies', {}):
        config['options']['python_requires'] = pyproject['tool']['poetry']['dependencies']['python']


def build_entry_points(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    setupcfg_scripts: Dict[str, str] = {}
    if 'options.entry_points' in config:
        setupcfg_scripts = dict(config['options.entry_points'].items())
    if 'scripts' in pyproject['tool']['poetry']:
        setupcfg_scripts['console_scripts'] = '\n'.join(
            [f'{k}={v}' for k, v in pyproject['tool']['poetry']['scripts'].items()])
    if 'plugins' in pyproject['tool']['poetry']:
        for section, commands in pyproject['tool']['poetry']['plugins'].items():
            setupcfg_scripts[section] = '\n'.join([f'{k}={v}' for k, v in commands.items()])

    config['options.entry_points'] = setupcfg_scripts


def gen_setup_cfg() -> None:
    # importing here rather than at top level because toml is not built-in
    check_manifest()
    import toml
    config = configparser.ConfigParser()
    config.read('setup.cfg')  # fine even if the file doesn't exist

    pyproject = toml.load('pyproject.toml')
    config['metadata'] = {k: v for k, v in pyproject['tool']['poetry'].items()
                          if k in ('name', 'version', 'description', 'authors')}

    build_packages(config, pyproject)
    build_entry_points(config, pyproject)

    with open('setup.cfg', 'w+') as f:
        config.write(f)

    with open('setup.cfg') as f:
        print("Generated setup.cfg:")
        print(f.read())


def check_manifest() -> None:
    # These files are mandatory for running. If they are not here, they are probably not in the manifest.
    for f in ('pyproject.toml', 'poetry.lock'):
        if not os.path.exists(f):
            raise RuntimeError(f"No {f} found in {os.getcwd()}. This file is required")


def convert_packages(pkgs: List[Dict[str, str]]) -> Dict[str, str]:
    actual = defaultdict(list)
    for pkg in pkgs:
        for k, v in pkg.items():
            if k == 'from':
                k = 'where'
            actual[k].append(v)
    return {k: ','.join(v) for k, v in actual.items()}


def gen_reqs() -> List[pkg_resources.Requirement]:
    try:
        out = subprocess.check_output('poetry export --without-hashes'.split(), encoding='utf-8')
    except subprocess.CalledProcessError as e:
        print("Raw output from poetry:", e.output)
        raise
    # Lockfile is out of date with pyproject.toml, this is also a failure condition
    if out.startswith('Warning: The lock file is not up to date with the latest changes in pyproject.toml.'
                      ' You may be getting outdated dependencies. Run update to update them.'):
        raise RuntimeError(
            'Warning: The lock file is not up to date with the latest changes in pyproject.toml.'
            ' You may be getting outdated dependencies. Run poetry update to update them.')
    reqs = []
    for line in out.split('\n'):
        try:
            reqs.extend(list(pkg_resources.parse_requirements(line)))
        except pkg_resources.extern.packaging.requirements.InvalidRequirement as e:
            # Poetry export starts with this preamble:
            # --extra-index-url http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple
            # or
            # --index-url http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple
            # depending on the specific configured sources which can't be parsed. But it can be ignored!
            if e.args[0].startswith('Parse error at "\'--extra-\'":'):
                continue
            elif e.args[0].startswith('Parse error at "\'--index-\'":'):
                continue
            print("Failed to parse requirement", line)
            raise

    return reqs


class ApplicationBuildMetaBackend(_BuildMetaBackend):

    def run_setup(self, setup_script='setup.py'):
        gen_setup_cfg()
        return super().run_setup(setup_script)

    def build_sdist(self, sdist_directory, config_settings=None):
        # just here to show that they are here
        return super().build_sdist(sdist_directory, config_settings)

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        # just here to show that they are here
        return super().build_wheel(wheel_directory, config_settings, metadata_directory)

    def prepare_metadata_for_build_wheel(self, metadata_directory, config_settings=None):
        # just here to show that they are here
        return super().prepare_metadata_for_build_wheel(metadata_directory, config_settings)

    def get_requires_for_build_wheel(self, config_settings=None):
        return ['setuptools', 'wheel >= 0.25', 'poetry', 'toml']

    def get_requires_for_build_sdist(self, config_settings=None):
        return ['setuptools', 'poetry', 'toml']


# The primary backend
_BACKEND = ApplicationBuildMetaBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist

