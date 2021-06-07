import subprocess
import tempfile
import zipfile
from argparse import ArgumentParser
from collections import defaultdict
from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pkginfo  # type: ignore
import toml
from pkg_resources import Requirement

try:
    import ppsetuptools as _  # type: ignore  # noqa
except ImportError:
    exit("Can not run conversion script without pep621 extra installed. Please install `vulcan[pep621]`")


def make_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('--shiv-console-scripts', action='store_true')
    return parser


def wheel() -> Tuple[pkginfo.Wheel, Dict[str, Dict[str, str]], List[str]]:

    with tempfile.TemporaryDirectory(suffix='.vulcan-migrate') as tmp:
        subprocess.run(['pip', 'wheel', '--no-deps', '-w', tmp, '.'])
        whl = pkginfo.Wheel(next(Path(tmp).glob('*.whl')))
        eps: Dict[str, Dict[str, str]] = defaultdict(dict)
        with zipfile.ZipFile(whl.filename) as zf:
            dist_info = f'{whl.name.replace("-", "_")}-{whl.version}.dist-info'
            try:
                with zf.open(f'{dist_info}/entry_points.txt') as f:
                    cp = ConfigParser()
                    cp.read_file(StringIO(f.read().decode()))
                    for section in cp.sections():
                        for key in cp[section]:
                            eps[section][key] = cp[section][key]
            except KeyError:
                eps = {}
            try:
                with zf.open(f'{dist_info}/top_level.txt') as f:
                    data = f.read().decode()
                    packages = [line.strip() for line in data.split('\n') if line.strip()]
            except KeyError:
                packages = []

    return whl, eps, packages


def contributors(author: Optional[str], author_email: Optional[str]) -> List[Dict[str, str]]:
    vals = {}
    if author:
        vals['name'] = author
    if author_email:
        vals['email'] = author_email
    return [vals]


def shiv_from_console_scripts(console_scripts: Dict[str, str]) -> List[Dict[str, str]]:
    shivs: List[Dict[str, str]] = []
    for name in console_scripts:
        shivs.append({
            'bin_name': name,
            'console_script': name,
            'interpreter': '/usr/bin/env python3.6'
        })
    return shivs


def convert() -> None:
    try:
        pyproject = toml.load('./pyproject.toml')
    except FileNotFoundError:
        pyproject = {}
    if 'project' in pyproject:
        exit('refusing to overwrite current project configuration')
    args = make_parser().parse_args()
    whl, entry_points, packages = wheel()
    project: Dict[str, Any] = {}
    vulcan: Dict[str, Any] = {}
    pyproject['project'] = project
    pyproject['tool'] = pyproject.get('tool', {})
    pyproject['tool']['vulcan'] = vulcan
    project['name'] = whl.name
    if whl.author or whl.author_email:
        project['authors'] = contributors(whl.author, whl.author_email)
    if whl.maintainer or whl.maintainer_email:
        project['maintainers'] = contributors(whl.maintainer, whl.maintainer_email)
    if whl.classifiers:
        project['classifiers'] = list(whl.classifiers)
    if whl.summary:
        project['description'] = whl.summary
    if whl.keywords:
        project['keywords'] = whl.keywords.split(',')
    if whl.license:
        project['license'] = whl.license
    if whl.project_urls:
        project['urls'] = {k: v for k, v in [u.split(', ') for u in whl.project_urls]}
    try:
        readme = next(p for p in Path().iterdir() if p.name.lower().startswith('readme'))
        project['readme'] = str(readme)
    except StopIteration:
        pass

    if whl.requires_dist:
        vulcan['dependencies'] = {}
        for req in whl.requires_dist:
            parsed_req = Requirement.parse(req)
            if '; extra == "' in str(parsed_req):
                # extra, swing back to this
                continue
            vulcan['dependencies'][parsed_req.name] = str(parsed_req.specifier)  # type: ignore
    if whl.provides_extras:
        vulcan['extras'] = {}
        for extra in whl.provides_extras:
            vulcan['extras'][extra] = []
            for req in whl.requires_dist:
                parsed_req = Requirement.parse(req)
                if f'; extra == "{extra}"' not in str(parsed_req):
                    # extra, swing back to this
                    continue
                vulcan['extras'][extra].append(f'{parsed_req.name}{parsed_req.specifier}')  # type: ignore
    if packages:
        vulcan['packages'] = packages
    if whl.requires_python:
        project['requires-python'] = whl.requires_python

    if 'console_scripts' in entry_points:
        project['scripts'] = entry_points['console_scripts']
        del entry_points['console_scripts']
    if 'gui_scripts' in entry_points:
        project['gui-scripts'] = entry_points['gui_scripts']
        del entry_points['gui_scripts']
    if entry_points:
        project['entry-points'] = entry_points
    if args.shiv_console_scripts:
        vulcan['shiv'] = shiv_from_console_scripts(project['scripts'])

    pyproject['build-system'] = {}
    pyproject['build-system']['requires'] = ['vulcan[pep621]>=1.7.0']
    pyproject['build-system']['build-backend'] = 'vulcan.build_backend'

    with open('./pyproject.toml', 'w+') as f:
        toml.dump(pyproject, f)
