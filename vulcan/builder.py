import asyncio
import tempfile
from itertools import chain
from typing import Dict, List, Tuple

from pkg_resources import Requirement

from vulcan.isolation import VulcanEnvBuilder, create_venv


async def build_requires(pipenv: VulcanEnvBuilder, requires: List[str]) -> Dict[str, Requirement]:
    with tempfile.TemporaryDirectory() as site_packages:
        await pipenv.install(site_packages, requires)
        freeze = await pipenv.freeze(site_packages)
        return freeze


async def resolve_deps(install_requires: List[str], extras: Dict[str, List[str]],
                       python_version: str = None
                       ) -> Tuple[List[str], Dict[str, List[str]]]:

    if not install_requires and not extras:
        return [], {}

    extras_list = list(extras.items())
    with create_venv(python_version) as pipenv:
        print("Building base requires")
        base_freeze = await build_requires(pipenv, install_requires)
        if not extras_list:
            # if we have no extras, we are done here.
            return sorted([str(req) for req in base_freeze.values()]), {}

        print("Building requirements for base + all extras")
        final_out_task = asyncio.get_event_loop().create_task(
            build_requires(
                pipenv,
                install_requires + list(chain.from_iterable(reqs for _, reqs in extras_list))))
        resolved_extras = {}
        for extra, extra_reqs in extras_list:
            # this is the expensive bit, because we create a new venv for each extra
            print(f"Building requirements for extra '{extra}'")
            resolved_extras[extra] = asyncio.get_event_loop().create_task(
                build_requires(pipenv, install_requires + extra_reqs))

        # It is important here to wait until ALL tasks are complete (return_exceptions=True) because on
        # windows, if that is not done then the TemporaryDirectory is create_venv will try to remove itself
        # while our async subprocesses still have a lock on the python.exe (windows-only issue). which then
        # causes more errors
        results = await asyncio.gather(*resolved_extras.values(), final_out_task, return_exceptions=True)
        for res in results:
            if isinstance(res, BaseException):
                raise res
        all_resolved = final_out_task.result()

        extras_out = {k: sorted([str(all_resolved[req]) for req in v.result()]) for k, v in
                      resolved_extras.items()}
        return sorted([str(all_resolved[req]) for req in base_freeze.keys()]), extras_out
