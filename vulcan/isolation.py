import shlex
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from os import PathLike
from types import SimpleNamespace
from typing import Dict, Generator, List, Union
from venv import EnvBuilder

from pkg_resources import Requirement


@contextmanager
def create_venv(python_version: str = None) -> Generator['VulcanEnvBuilder', None, None]:
    with tempfile.TemporaryDirectory(prefix='vulcan-build-') as tempdir:
        builder = VulcanEnvBuilder(with_pip=True, python_version=python_version)
        builder.create(tempdir)
        yield builder


def get_executable(version: str) -> str:
    if sys.platform == 'win32':
        which = 'where'
    else:
        which = 'which'
    return subprocess.check_output(
        [which, f'python{version}'], encoding='utf-8', stderr=subprocess.PIPE).strip()


@contextmanager
def patch_executable(python_version: str = None) -> Generator[None, None, None]:
    if python_version is None:
        yield
    else:
        try:
            if sys.version_info >= (3, 8):
                # for some reason mypy thinks this is incorrect for 3.8
                # even though it is definitely correct and I've read the code showing it
                # So this whole file disables the "warn_unused_ignore" config due to these 2 lines :(
                old_exe = sys._base_executable  # type: ignore
                sys._base_executable = get_executable(python_version)  # type: ignore
            else:
                old_exe = sys.executable
                sys.executable = get_executable(python_version)
            yield
        except subprocess.CalledProcessError as e:
            print(f"Command '{' '.join(shlex.quote(a) for a in e.cmd)}' failed with exit code {e.returncode}")
            print(e.stderr)
            exit(1)
        finally:
            if sys.version_info >= (3, 8):
                sys._base_executable = old_exe  # type: ignore
            else:
                sys.executable = old_exe


class VulcanEnvBuilder(EnvBuilder):

    def __init__(self, system_site_packages: bool = False, clear: bool = False,
                 symlinks: bool = False, upgrade: bool = False, with_pip: bool = False, prompt: str = None,
                 python_version: str = None):
        self.context: SimpleNamespace
        super().__init__(system_site_packages=system_site_packages, clear=clear, symlinks=symlinks,
                         upgrade=upgrade, with_pip=with_pip, prompt=prompt)
        self._executable_python_version = python_version

    def ensure_directories(self,
                           env_dir: Union[str, bytes, 'PathLike[str]', 'PathLike[bytes]']
                           ) -> SimpleNamespace:
        with patch_executable(self._executable_python_version):
            self.context = super().ensure_directories(env_dir)
        return self.context

    def _setup_pip(self, context: SimpleNamespace) -> None:
        super()._setup_pip(context)
        cmd = [context.env_exe, '-Im', 'pip', 'install', '--upgrade', 'pip']
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
            '--use-pep517',
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
