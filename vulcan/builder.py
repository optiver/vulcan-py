import subprocess
from itertools import chain
from pathlib import Path
from typing import Dict, List, Tuple

import build.env
from pkg_resources import Requirement


def get_freeze(env: build.env._IsolatedEnvVenvPip, site_packages: Path) -> Dict[str, Requirement]:
    frozen = subprocess.check_output(
        [env._pip_executable, '-m', 'pip', 'list', '--format=freeze', '--path', str(site_packages)],
        encoding='utf-8')
    reqs = [Requirement.parse(line) for line in frozen.split('\n') if line]
    return {req.name: req for req in reqs}  # type: ignore


def resolve_deps(install_requires: List[str], extras: Dict[str, List[str]]
                 ) -> Tuple[List[str], Dict[str, List[str]]]:
    builder = build.env.IsolatedEnvBuilder()
    pipenv: build.env._IsolatedEnvVenvPip

    if not install_requires and not extras:
        return [], {}

    extras_list = list(extras.items())
    with builder as pipenv:  # type: ignore
        site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
        pipenv.install(install_requires)
        base_freeze = get_freeze(pipenv, site_packages)
        if not extras_list:
            # if we have no extras, we are done here.
            return sorted([str(req) for req in base_freeze.values()]), {}
        # for the first extra, we can use the virtualenv because the extra_reqs are by definition a superset
        # of the base reqs
        extra, extra_reqs = extras_list[0]
        pipenv.install(install_requires + extra_reqs)
        extra_freeze = get_freeze(pipenv, site_packages)
        resolved_extras = {extra: sorted([str(req) for req in extra_freeze.values()])}
        if len(extras_list) == 1:
            # if we have exactly 1 extra, we can get away with only using 1 venv in total
            return sorted([str(extra_freeze[req]) for req in base_freeze.keys()]), resolved_extras

        # otherwise, we make one last use of this venv to get the total deps of all the extras installed at
        # the same time ( this will be used to get the actual versions of the reqs )
        pipenv.install(install_requires + list(chain.from_iterable(reqs for _, reqs in extras_list[1:])))
        all_resolved = get_freeze(pipenv, site_packages)

    # skipping the first extra because we've already done that one.
    for extra, extra_reqs in extras_list[1:]:
        with builder as pipenv:  # type: ignore
            # this is the expensive bit, because we create a new venv for each extra beyond the first, so
            # total venvs is max(1, len(extras))
            site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
            pipenv.install(install_requires + extra_reqs)
            extra_freeze = get_freeze(pipenv, site_packages)
            resolved_extras[extra] = sorted([str(all_resolved[req]) for req in extra_freeze])

    return sorted([str(all_resolved[req]) for req in base_freeze.keys()]), resolved_extras
