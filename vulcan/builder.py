import subprocess
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
    all_resolved: Dict[str, Requirement] = {}
    with builder as pipenv:  # type: ignore
        site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
        pipenv.install(install_requires)
        base_deps = get_freeze(pipenv, site_packages)
        if not extras:
            return [str(req) for req in base_deps], {}
        elif len(extras) <= 1:
            # if there are 0 or 1 extras, we can get away with only a single venv
            # extras is guarenteed to only have one key now
            extra, extra_deps = next(iter(extras.items()))
            pipenv.install(extra_deps)
            all_resolved = get_freeze(pipenv, site_packages)
            extras_only = {name: req for name, req in all_resolved.items() if name not in base_deps}
            return [str(req) for name, req in all_resolved.items() if name not in extras_only], {
                extra: [str(all_resolved[req]) for req in extras_only]}
    # there are 2+ extras, and we have now resolved the base dependencies and none of the extras
    # (this is the slow path)
    all_resolved_extras = {}
    for extra, configured_deps in extras.items():
        with builder as pipenv:  # type: ignore
            site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
            # base deps instead of install_requires to make sure we're not conflicting
            pipenv.install(base_deps)
            pipenv.install(configured_deps)
            all_resolved_extras[extra] = get_freeze(pipenv, site_packages)

    with builder as pipenv:  # type: ignore
        pipenv.install(install_requires)
        for reqs in extras.values():
            site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
            pipenv.install(reqs)
        all_installed = get_freeze(pipenv, site_packages)

    consolidated = {}
    names = set()
    for extra, resolved_reqs in all_resolved_extras.items():
        names |= set(resolved_reqs)
        consolidated[extra] = sorted([str(all_installed[name]) for name in resolved_reqs])

    return sorted([str(all_installed[name]) for name in base_deps]), consolidated
