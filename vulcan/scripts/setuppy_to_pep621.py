import subprocess
import tempfile
import zipfile
from collections import defaultdict
from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pkginfo  # type: ignore
import toml
from pkg_resources import Requirement


def wheel() -> Tuple[pkginfo.Wheel, Dict[str, Dict[str, str]]]:

    with tempfile.TemporaryDirectory(suffix='.vulcan-migrate') as tmp:
        subprocess.run(['pip', 'wheel', '--no-deps', '-w', tmp, '.'])
        whl = pkginfo.Wheel(next(Path(tmp).glob('*.whl')))
        eps: Dict[str, Dict[str, str]] = defaultdict(dict)
        try:
            with zipfile.ZipFile(whl.filename) as zf:
                with zf.open(f'{whl.name.replace("-", "_")}-{whl.version}.dist-info/entry_points.txt') as f:
                    cp = ConfigParser()
                    cp.read_file(StringIO(f.read().decode()))
                    for section in cp.sections():
                        for key in cp[section]:
                            eps[section][key] = cp[section][key]
        except KeyError:
            eps = {}

    return whl, eps


def contributors(author: Optional[str], author_email: Optional[str]) -> List[Dict[str, str]]:
    vals = {}
    if author:
        vals['name'] = author
    if author_email:
        vals['email'] = author_email
    return [vals]


def convert() -> None:
    try:
        pyproject = toml.load('./pyproject.toml')
    except FileNotFoundError:
        pyproject = {}
    if 'project' in pyproject:
        exit('refusing to overwrite current project configuration')
    whl, entry_points = wheel()
    project: Dict[str, Any] = {}
    vulcan: Dict[str, Any] = {}
    pyproject['project'] = project
    pyproject['tool'] = {}
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
        project['keywords'] = list(whl.keywords)
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

    pyproject['build-system'] = {}
    pyproject['build-system']['requires'] = ['vulcan']
    pyproject['build-system']['build_backen'] = 'vulcan.build_backend'

    with open('./pyproject.toml', 'w+') as f:
        toml.dump(pyproject, f)
