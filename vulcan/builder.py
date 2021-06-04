import tempfile
from itertools import chain
from typing import Dict, List, Tuple

from vulcan.isolation import create_venv


def resolve_deps(install_requires: List[str], extras: Dict[str, List[str]],
                 python_version: str = None
                 ) -> Tuple[List[str], Dict[str, List[str]]]:

    if not install_requires and not extras:
        return [], {}

    extras_list = list(extras.items())
    with create_venv(python_version) as pipenv:
        with tempfile.TemporaryDirectory() as site_packages:
            print("Building default requirements")
            pipenv.install(site_packages, install_requires)
            base_freeze = pipenv.freeze(site_packages)
            if not extras_list:
                # if we have no extras, we are done here.
                return sorted([str(req) for req in base_freeze.values()]), {}

        with tempfile.TemporaryDirectory() as site_packages:
            print("Building final resolved packages")
            pipenv.install(site_packages,
                           install_requires + list(chain.from_iterable(reqs for _, reqs in extras_list)))
            all_resolved = pipenv.freeze(site_packages)

        resolved_extras = {}
        for extra, extra_reqs in extras_list:
            with tempfile.TemporaryDirectory() as site_packages:
                # this is the expensive bit, because we create a new venv for each extra
                print(f"Building requirements for extra '{extra}'")
                pipenv.install(site_packages, install_requires + extra_reqs)
                extra_freeze = pipenv.freeze(site_packages)
                resolved_extras[extra] = sorted([str(all_resolved[req]) for req in extra_freeze])

        return sorted([str(all_resolved[req]) for req in base_freeze.keys()]), resolved_extras
