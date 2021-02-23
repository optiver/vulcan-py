import subprocess
import tempfile
from contextlib import contextmanager
from os import PathLike
from types import SimpleNamespace
from typing import Dict, Generator, List, Union
from venv import EnvBuilder

from pkg_resources import Requirement


@contextmanager
def create_venv() -> Generator['VulcanEnvBuilder', None, None]:
    with tempfile.TemporaryDirectory(prefix='vulcan-build-') as tempdir:
        builder = VulcanEnvBuilder(with_pip=True)
        builder.create(tempdir)
        yield builder


class VulcanEnvBuilder(EnvBuilder):

    def __init__(self, system_site_packages: bool = False, clear: bool = False,
                 symlinks: bool = False, upgrade: bool = False, with_pip: bool = False, prompt: str = None):
        self.context: SimpleNamespace
        super().__init__(system_site_packages=system_site_packages, clear=clear, symlinks=symlinks,
                         upgrade=upgrade, with_pip=with_pip, prompt=prompt)

    def ensure_directories(self,
                           env_dir: Union[str, bytes, 'PathLike[str]', 'PathLike[bytes]']
                           ) -> SimpleNamespace:
        self.context = super().ensure_directories(env_dir)
        return self.context

    def _setup_pip(self, context: SimpleNamespace) -> None:
        super()._setup_pip(context)
        cmd = [context.env_exe, '-Im', 'pip', '--upgrade', 'pip']
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def install(self, deps_dir: Union[str, bytes, 'PathLike[str]', 'PathLike[bytes]'], requirements: List[str]
                ) -> None:
        # install Isolated with module pip using pep517
        if not requirements:
            return
        cmd = [
            self.context.env_exe,
            '-Im',
            'pip',
            'install',
            '--target',
            str(deps_dir)] + requirements
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def freeze(self, deps_dir: Union[str, bytes, 'PathLike[str]', 'PathLike[bytes]']
               ) -> Dict[str, Requirement]:
        # list with the requirements.txt format only libraries installed in specifically this venv
        cmd = [self.context.env_exe, '-Im', 'pip', 'list', '--format=freeze', '--path', str(deps_dir)]
        frozen = subprocess.check_output(cmd, encoding='utf-8')
        reqs = [Requirement.parse(line) for line in frozen.split('\n') if line]
        return {req.name: req for req in reqs}  # type: ignore
