import tempfile
from itertools import chain
from typing import Dict, List, Tuple

from vulcan.isolation import create_venv


def resolve_deps(install_requires: List[str], extras: Dict[str, List[str]]
                 ) -> Tuple[List[str], Dict[str, List[str]]]:

    if not install_requires and not extras:
        return [], {}

    extras_list = list(extras.items())
    with create_venv() as pipenv:
        with tempfile.TemporaryDirectory() as site_packages:
            pipenv.install(site_packages, install_requires)
            base_freeze = pipenv.freeze(site_packages)
            if not extras_list:
                # if we have no extras, we are done here.
                return sorted([str(req) for req in base_freeze.values()]), {}
            # for the first extra, we can use the virtualenv because the extra_reqs are by definition a
            # superset of the base reqs
            extra, extra_reqs = extras_list[0]
            pipenv.install(site_packages, install_requires + extra_reqs)
            extra_freeze = pipenv.freeze(site_packages)
            resolved_extras = {extra: sorted([str(req) for req in extra_freeze.values()])}
            if len(extras_list) == 1:
                # if we have exactly 1 extra, we can get away with only using 1 venv in total
                return sorted([str(extra_freeze[req]) for req in base_freeze.keys()]), resolved_extras

            # otherwise, we make one last use of this venv to get the total deps of all the extras installed
            # at the same time ( this will be used to get the actual versions of the reqs )
            pipenv.install(site_packages,
                           install_requires + list(chain.from_iterable(reqs for _, reqs in extras_list)))
            all_resolved = pipenv.freeze(site_packages)

        # skipping the first extra because we've already done that one.
        for extra, extra_reqs in extras_list[1:]:
            with tempfile.TemporaryDirectory() as site_packages:
                # this is the expensive bit, because we create a new venv for each extra beyond the first, so
                # total venvs is max(1, len(extras))
                pipenv.install(site_packages, install_requires + extra_reqs)
                extra_freeze = pipenv.freeze(site_packages)
                resolved_extras[extra] = sorted([str(all_resolved[req]) for req in extra_freeze])

        return sorted([str(all_resolved[req]) for req in base_freeze.keys()]), resolved_extras
