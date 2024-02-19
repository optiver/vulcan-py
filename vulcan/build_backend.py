from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Generator

from editables import EditableProject

from vulcan import Vulcan
from vulcan.plugins import PluginRunner

__all__ = ["build_wheel", "build_sdist"]


@contextmanager
def patch_argv(argv: list[str]) -> Generator[None, None, None]:
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + argv
    yield
    sys.argv = old_argv


def build(outdir: str, config_settings: dict[str, str] | None = None) -> str:
    config = Vulcan.from_source(Path().absolute())

    # https://setuptools.readthedocs.io/en/latest/userguide/keywords.html
    # https://docs.python.org/3/distutils/apiref.html
    with PluginRunner(config):
        dist = config.setup(config_settings=config_settings)
    rel_dist = Path(dist.dist_files[0][-1])
    shutil.move(str(rel_dist), Path(outdir) / rel_dist.name)
    return rel_dist.name


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    with patch_argv(["bdist_wheel"]):
        return build(wheel_directory, config_settings)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, str] | None = None,
) -> str:
    with patch_argv(["sdist"]):
        return build(sdist_directory, config_settings)


def get_virtualenv_python() -> Path:
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env is None:
        raise RuntimeError("No virtualenv active")
    if sys.platform == "win32":
        # sigh
        return Path(virtual_env, "Scripts", "python")
    else:
        # if this isn't in an else,
        # mypy complains on windows that it is unreachable
        return Path(virtual_env, "bin", "python")


# tox requires these two for some reason :(
def get_requires_for_build_sdist(config_settings: dict[str, str] | None = None) -> list[str]:
    return []


def get_requires_for_build_wheel(config_settings: dict[str, str] | None = None) -> list[str]:
    return []


def get_pip_version(python_callable: Path) -> tuple[int, ...] | None:
    out = subprocess.check_output([str(python_callable), "-m", "pip", "--version"], encoding="utf-8")
    m = re.search(r"pip (\d+\.\d+(\.\d+)?)", out)
    if not m:
        return None
    return tuple((int(n) for n in m.group(1).split(".")))


# pep660 functions
def unpack(whl: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_output(f"wheel unpack {whl} -d {tmp}".split())
        unpacked = list(Path(tmp).glob("*"))
        assert len(unpacked) == 1
        shutil.copytree(unpacked[0], whl.parent / unpacked[0].name)
        return whl.parent / unpacked[0].name


def pack(unpacked_wheel: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_output(f"wheel pack {unpacked_wheel} -d {tmp}".split())
        packed = list(Path(tmp).glob("*.whl"))
        assert len(packed) == 1
        shutil.copy(packed[0], unpacked_wheel.parent)
        return unpacked_wheel.parent / packed[0].name


def add_requirement(unpacked_whl_dir: Path, req: str) -> None:
    metadata = next(unpacked_whl_dir.glob("*.dist-info")) / "METADATA"  # is mandatory
    with metadata.open() as f:
        metadata_lines = list(f)
    i = 0
    for i, line in enumerate(metadata_lines):
        if not (line.strip() and not line.startswith("Requires-Dist: ")):
            # find the start of the requires-dist, or the end of the metadata keys
            break
    metadata_lines.insert(i, f"Requires-Dist: {req}\n")
    metadata.write_text("".join(metadata_lines))


def _find_local_package(name: str) -> Path:
    """
    Try and find the local package being refered to for editable. Default to ./{name} if we can't find it otherwise.
    """
    return next(Path().rglob(name), Path(name))


def make_editable(whl: Path) -> None:
    unpacked_whl_dir = unpack(whl)
    add_requirement(unpacked_whl_dir, f"editables (~={version('editables')})")
    # https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode
    # this is guarenteed to exist, name is extremely mandatory. Can't make a valid wheel without it.
    # it might be UNKNOWN, but this is user error.
    name = next(
        line.split(":")[1].strip()
        for line in (next(unpacked_whl_dir.glob("*.dist-info")) / "METADATA").read_text().splitlines()
        if "Name:" in line
    )
    project_name = re.sub(r"[^\w\d.]+", "_", name, re.UNICODE)
    project = EditableProject(project_name, Path().absolute())
    packages = (p for p in unpacked_whl_dir.iterdir() if not p.name.endswith(".dist-info"))
    for package in packages:
        project.map(package.name, _find_local_package(package.name))
        # removing the actual code packages because they will conflict with the .pth files, and take
        # precendence over them
        shutil.rmtree(unpacked_whl_dir / package.name)

    # None of the IDEs/static type tools support PEP 660
    # As a fall-back for static analysis also provide the path in the .pth file
    # https://github.com/microsoft/pylance-release/blob/main/TROUBLESHOOTING.md#editable-install-modules-not-found
    project.add_to_path(project.project_dir)

    for name, content in project.files():
        (unpacked_whl_dir / name).write_text(content)

    assert whl == pack(unpacked_whl_dir), "pre-wheel and post-wheel should be the same path"
    shutil.rmtree(unpacked_whl_dir)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, str] | None = None,
    metadata_directory: str | None = None,
) -> str:
    whl_path = Path(wheel_directory) / build_wheel(wheel_directory, config_settings, metadata_directory)
    make_editable(whl_path)
    return whl_path.name
