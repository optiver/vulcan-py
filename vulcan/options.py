import configparser
import subprocess
from collections import defaultdict
from typing import Any, Dict, List, Mapping

import pkg_resources
import pkg_resources.extern  # type: ignore


def convert_packages(pkgs: List[Dict[str, str]]) -> Dict[str, str]:
    actual = defaultdict(list)
    for pkg in pkgs:
        for k, v in pkg.items():
            if k == 'from':
                # why did they change only this one? no idea
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
            if e.args[0].startswith(('Parse error at "\'--extra-\'":',
                                     'Parse error at "\'--index-\'":')):
                print(f"Skipping line {line!r}, matches index specifiers")
                continue
            print("Failed to parse requirement", line)
            raise

    return reqs


def build_entry_points(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    setupcfg_scripts: Dict[str, str] = {}
    if 'options.entry_points' in config:
        # preserve entry points that are configured in setup.cfg that happens to exist
        setupcfg_scripts = dict(config['options.entry_points'].items())
    if 'scripts' in pyproject['tool']['poetry']:
        # poetry special-cases console_scripts entry-points. If pyproject.toml sets this, override setup.cfg
        setupcfg_scripts['console_scripts'] = '\n'.join(
            [f'{k}={v}' for k, v in pyproject['tool']['poetry']['scripts'].items()])
    if 'plugins' in pyproject['tool']['poetry']:
        # same thing for the rest of the entry_point groups. Don't bother to merge, that'll get confusing
        # just print when there is conflict
        for section, commands in pyproject['tool']['poetry']['plugins'].items():
            if section in setupcfg_scripts:
                print(f"Overlapping entry_point group {section} in pyproject.toml and setup.cfg."
                      " Prefering pyproject.toml")
            setupcfg_scripts[section] = '\n'.join([f'{k}={v}' for k, v in commands.items()])

    config['options.entry_points'] = setupcfg_scripts


def build_packages(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    if not config.has_section('options'):
        config['options'] = {}
    if 'install_requires' in config['options']:
        print(f"Overwriting install_requires {config['options']['install_requires']}")
    config['options']['install_requires'] = '\n'.join([str(req) for req in gen_reqs()])
    find = False
    # next 2 ifs are the equivilent of find_packages('.') by default, prefering any configured values
    if 'packages' not in config['options']:
        find = True
        config['options']['packages'] = 'find:'

    if 'packages' in pyproject['tool']['poetry'] and find:
        config['options.packages.find'] = convert_packages(pyproject['tool']['poetry']['packages'])

    if 'python' in pyproject['tool']['poetry'].get('dependencies', {}):
        # for some reason poetry likes to specify the python version the same as library versions. I think
        # this is wierd and setuptools does this better.
        # Not that that matters, need to move it regardless.
        config['options']['python_requires'] = pyproject['tool']['poetry']['dependencies']['python']


def build_package_data(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    if not config.has_section('options'):
        config['options'] = {}
    # not letting this be configurable, use MANIFEST.in to control what actually gets included.
    if 'include' in pyproject['tool']['poetry'] or 'exclude' in pyproject['tool']['poetry']:
        raise ValueError(
            "'include' and 'exclude' keys in [tool.poetry] section are not allowed with vulcan."
            "Please use MANIFEST.in to include or exclude data files")
    config['options']['include_package_data'] = 'true'
