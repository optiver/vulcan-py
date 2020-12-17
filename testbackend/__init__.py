import io
import os
import subprocess
from textwrap import dedent

import pkg_resources
import pkg_resources.extern  # type: ignore
from setuptools.build_meta import _BuildMetaBackend  # type: ignore

__all__ = ['get_requires_for_build_sdist',
           'get_requires_for_build_wheel',
           'prepare_metadata_for_build_wheel',
           'build_wheel',
           'build_sdist']


def _open_setup_script(setup_script):
    if not os.path.exists(setup_script):
        # Supply a default setup.py
        return gen_setup()
    raise RuntimeError(
        "TestBackend is not compatible with setup.py, please migrate to setup.cfg or pyproject.toml")


def gen_setup():
    if not os.path.exists('poetry.lock'):
        # If this is not already present, poetry will
        #   a) try to generate it, and
        #   b) _say_ that it is trying to generate it on stdout
        raise RuntimeError(f"No poetry.lock found in {os.getcwd()}")
    try:
        out = subprocess.check_output('poetry export --without-hashes'.split(), encoding='utf-8')
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise
    reqs = []
    for line in out.split('\n'):
        try:
            reqs.extend(list(pkg_resources.parse_requirements(line)))
        except pkg_resources.extern.packaging.requirements.InvalidRequirement as e:
            # Poetry export starts with this preamble:
            # --extra-index-url http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple
            #
            # which can't be parsed. But it can be ignored!
            if e.args[0].startswith('Parse error at "\'--extra-\'":'):
                continue
            raise
    return io.StringIO(dedent(f"""\
        from setuptools import setup
        setup(
            install_requires={repr([str(r) for r in reqs])}
            )
        """))


class ApplicationBuildMetaBackend(_BuildMetaBackend):

    def run_setup(self, setup_script='setup.py'):
        # NOTE: This function is copy/pasted from the parent impl, the difference is that the
        # _open_setup_script is modified above
        __file__ = setup_script
        __name__ = '__main__'

        with _open_setup_script(__file__) as f:
            code = f.read().replace(r'\r\n', r'\n')

        exec(compile(code, __file__, 'exec'), locals())

    def get_requires_for_build_wheel(self, config_settings=None):
        return ['wheel', 'poetry']

    def get_requires_for_build_sdist(self, config_settings=None):
        return ['poetry']


# The primary backend
_BACKEND = ApplicationBuildMetaBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist
