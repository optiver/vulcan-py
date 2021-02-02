import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import build.env


def get_freeze(env: build.env._IsolatedEnvVenvPip, site_packages: Path) -> List[str]:
    frozen = subprocess.check_output(
        [env._pip_executable, '-m', 'pip', 'list', '--format=freeze', '--path', str(site_packages)],
        encoding='utf-8')
    return [line for line in frozen.split('\n') if line]


def resolve_deps(install_requires: List[str], extras: Dict[str, List[str]]
                 ) -> Tuple[List[str], Dict[str, List[str]]]:
    builder = build.env.IsolatedEnvBuilder()
    all_deps: List[str] = []
    pipenv: build.env._IsolatedEnvVenvPip
    with builder as pipenv:  # type: ignore
        site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
        pipenv.install(install_requires)
        base_deps = set(get_freeze(pipenv, site_packages))
        if not extras:
            return list(base_deps), {}
        elif len(extras) <= 1:
            # if there are 0 or 1 extras, we can get away with only a single venv
            # extras is guarenteed to only have one key now
            extra, extra_deps = next(iter(extras.items()))
            pipenv.install(extra_deps)
            all_deps.extend(base_deps)
            resolved_extras = set(get_freeze(pipenv, site_packages))
            return list(base_deps), {extra: list(resolved_extras - base_deps)}
    # there are 2+ extras, and we have now resolved the base dependencies and none of the extras
    # (this is the slow path)
    all_resolved_extras = {}
    for extra, configured_deps in extras.items():
        with builder as pipenv:  # type: ignore
            site_packages = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
            # base deps instead of install_requires to make sure we're not conflicting
            pipenv.install(base_deps)
            pipenv.install(configured_deps)
            all_resolved_extras[extra] = list(set(get_freeze(pipenv, site_packages)) - base_deps)
    return list(base_deps), all_resolved_extras
