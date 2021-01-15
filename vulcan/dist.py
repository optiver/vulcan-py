import os
import shutil
import shlex
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Type, TypeVar

import pkg_resources
import pkg_resources.extern  # type: ignore
from pkg_resources import Requirement
from vulcan import __VERSION__

T = TypeVar('T', bound='Dist')


def gen_reqs() -> List[pkg_resources.Requirement]:
    try:
        out = subprocess.check_output('poetry export --without-hashes'.split(), encoding='utf-8')
    except subprocess.CalledProcessError as e:
        print("Raw output from poetry:", e.output)
        raise
    # Lockfile is out of date with pyproject.toml, this is also a failure condition
    if out.startswith('Warning: The lock file is not up to date with the latest changes in pyproject.toml.'
                      ' You may be getting outdated dependencies. Run update to update them.'):
        raise RuntimeError(
            'Warning: The lock file is not up to date with the latest changes in pyproject.toml.'
            ' You may be getting outdated dependencies. Run poetry update to update them.')
    reqs = []
    for line in out.split('\n'):
        try:
            reqs.extend(list(pkg_resources.parse_requirements(line)))
        except pkg_resources.extern.packaging.requirements.InvalidRequirement as e:
            # Poetry export starts with this preamble:
            # --extra-index-url http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple
            # or
            # --index-url http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple
            # depending on the specific configured sources which can't be parsed. But it can be ignored!
            if e.args[0].startswith(('Parse error at "\'--extra-\'":',
                                     'Parse error at "\'--index-\'":')):
                print(f"Skipping line {line!r}, matches index specifiers")
                continue
            print("Failed to parse requirement", line)
            raise

    return reqs


@contextmanager
def chdir(dest: Path) -> Generator[None, None, None]:
    old = os.getcwd()
    os.chdir(dest)
    yield
    os.chdir(old)


class Dist:
    def __init__(self, unpacked_wheel: Path) -> None:
        self._unpacked = unpacked_wheel
        self.build_tool = f'vulcan {__VERSION__}'
        self.metadata_file: Path

    @classmethod
    @contextmanager
    def unpack(cls: Type[T], target: Path) -> Generator[T, None, None]:
        raise NotImplementedError

    def fix_metadata(self, new_requirements: List[Requirement]) -> None:
        lines = []
        with self.metadata_file.open() as metadata:
            replaced = False
            print("BEFORE:")
            for line in metadata:
                print(line, end='')
                if line.startswith('Requires-Dist:'):
                    if replaced:
                        continue
                    replaced = True
                    for req in new_requirements:
                        lines.append(f'Requires-Dist: {str(req)}\n')
                    continue
                lines.append(line)

            if not replaced:
                for req in new_requirements:
                    lines.append(f'Requires-Dist: {str(req)}\n')

        with self.metadata_file.open('w+') as metadata:
            print("AFTER:")
            print(''.join(lines))
            metadata.write(''.join(lines))


class Wheel(Dist):
    def __init__(self, unpacked_wheel: Path) -> None:
        super().__init__(unpacked_wheel)
        self.metadata_file = self._unpacked / f'{self._unpacked.name}.dist-info/METADATA'

    @classmethod
    @contextmanager
    def unpack(cls: Type[T], target: Path) -> Generator[T, None, None]:
        with chdir(target.parent):
            subprocess.run(['wheel', 'unpack', shlex.quote(str(target))],
                           encoding='utf-8', check=True)
            unpacked = next((i for i in Path().iterdir() if i.is_dir()))
            yield cls(unpacked)
            print("Repacking wheel")
            subprocess.run(['wheel', 'pack', shlex.quote(str(unpacked))],
                           encoding='utf-8', check=True)
            shutil.rmtree(unpacked)


class SDist(Dist):
    def __init__(self, unpacked_wheel: Path) -> None:
        super().__init__(unpacked_wheel)
        self.metadata_file = self._unpacked / 'PKG-INFO'

    @classmethod
    @contextmanager
    def unpack(cls: Type[T], target: Path) -> Generator[T, None, None]:
        with chdir(target.parent):
            print("MEMEMEMEMEMEME", target, os.listdir())
            subprocess.run(['tar', '-xf', shlex.quote(str(target))],
                           encoding='utf-8', check=True, stdout=subprocess.PIPE)
            unpacked = next((i for i in Path().iterdir() if i.is_dir()))
            yield cls(Path(unpacked))
            subprocess.run(['tar', '-zcf', shlex.quote(str(target)), shlex.quote(str(unpacked))],
                           encoding='utf-8', check=True)
            shutil.rmtree(unpacked)
