import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, cast

import setuptools
import tomlkit
from editables import EditableProject  # type: ignore
from ppsetuptools.ppsetuptools import _parse_kwargs  # type: ignore

from vulcan import Vulcan, flatten_reqs
from vulcan.plugins import PluginRunner

version: Callable[[str], str]
if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version


def _filter_nones(vals_dict: Dict[str, Optional[Any]]) -> Dict[str, Any]:
    return {k: v for k, v in vals_dict.items() if v is not None}


def setup(**kwargs: Any) -> Any:

    with open('pyproject.toml', 'r') as pptoml:
        pyproject_data = cast(Dict[str, Any], tomlkit.parse(pptoml.read()))

    if 'project' in pyproject_data:
        if 'dependencies' in pyproject_data['project']:
            raise RuntimeError("May not use [project]:dependencies key with vulcan")
        if 'optional-dependencies' in pyproject_data['project']:
            raise RuntimeError("May not use [project]:optional-dependencies key with vulcan")
        parsed_kwargs = _parse_kwargs(pyproject_data['project'], '.')
        parsed_kwargs.update(_filter_nones(kwargs))
        parsed_kwargs = _filter_nones(parsed_kwargs)
        # ppsetuptools doesn't handle entry points correctly
        if 'scripts' in parsed_kwargs:
            if 'entry_points' not in parsed_kwargs:
                parsed_kwargs['entry_points'] = {}
            parsed_kwargs['entry_points']['console_scripts'] = parsed_kwargs['scripts']
            del parsed_kwargs['scripts']
        if 'gui-scripts' in parsed_kwargs:
            parsed_kwargs['entry_points']['gui_scripts'] = parsed_kwargs['gui-scripts']
            del parsed_kwargs['gui-scripts']
        if 'entry_points' in parsed_kwargs:
            for ep_group in list(parsed_kwargs['entry_points']):
                parsed_kwargs['entry_points'][ep_group] = [
                    f'{k}={v}' for k, v in parsed_kwargs['entry_points'][ep_group].items()]
        return setuptools.setup(**parsed_kwargs)
    else:
        return setuptools.setup(**_filter_nones(kwargs))


__all__ = ['build_wheel',
           'build_sdist']


@contextmanager
def patch_argv(argv: List[str]) -> Generator[None, None, None]:
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0]] + argv
    yield
    sys.argv = old_argv


def build(outdir: str, config_settings: Dict[str, str] = None) -> str:
    config = Vulcan.from_source(Path().absolute())
    options: Dict[str, Any] = {}
    if config.packages:
        options['packages'] = config.packages
    if config.version:
        options['version'] = config.version

    if config.no_lock or (config_settings and config_settings.get('no-lock') == 'true'):
        options['install_requires'] = flatten_reqs(config.configured_dependencies)
        options['extras_require'] = config.configured_extras
    else:
        options['install_requires'] = config.dependencies
        options['extras_require'] = config.extras

    # https://setuptools.readthedocs.io/en/latest/userguide/keywords.html
    # https://docs.python.org/3/distutils/apiref.html
    with PluginRunner(config):
        dist = setup(**options, include_package_data=True)
    rel_dist = Path(dist.dist_files[0][-1])
    shutil.move(str(rel_dist), Path(outdir) / rel_dist.name)
    return rel_dist.name


def build_wheel(wheel_directory: str, config_settings: Dict[str, str] = None,
                metadata_directory: str = None) -> str:
    with patch_argv(['bdist_wheel']):
        return build(wheel_directory, config_settings)


def build_sdist(sdist_directory: str,
                config_settings: Dict[str, str] = None,
                ) -> str:
    with patch_argv(['sdist']):
        return build(sdist_directory, config_settings)


def get_virtualenv_python() -> Path:
    virtual_env = os.environ.get('VIRTUAL_ENV')
    if virtual_env is None:
        raise RuntimeError("No virtualenv active")
    if sys.platform == 'win32':
        # sigh
        return Path(virtual_env, 'Scripts', 'python')
    else:
        # if this isn't in an else,
        # mypy complains on windows that it is unreachable
        return Path(virtual_env, 'bin', 'python')


# tox requires these two for some reason :(
def get_requires_for_build_sdist(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def get_requires_for_build_wheel(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def get_pip_version(python_callable: Path) -> Optional[Tuple[int, ...]]:
    out = subprocess.check_output([str(python_callable), '-m', 'pip', '--version'], encoding='utf-8')
    m = re.search(r'pip (\d+\.\d+(\.\d+)?)', out)
    if not m:
        return None
    return tuple((int(n) for n in m.group(1).split('.')))


@contextmanager
def maybe_gen_setuppy(venv: Path, config: Vulcan) -> Generator[None, None, None]:
    pip_version = get_pip_version(venv)
    if pip_version is None or pip_version < (21, 3):
        print(f"pip version {pip_version} does not support editable installs for PEP517 projects,"
              " falling back to generated setup.py")
        options: Dict[str, Any] = {}
        if config.packages:
            options['packages'] = config.packages
        if config.version:
            options['version'] = config.version

        if config.no_lock:
            options['install_requires'] = flatten_reqs(config.configured_dependencies)
            options['extras_require'] = config.configured_extras
        else:
            options['install_requires'] = config.dependencies
            options['extras_require'] = config.extras

        setup = Path('setup.py')
        if setup.exists():
            exit('may not use vulcan develop when setup.py is present')
        try:
            with tempfile.NamedTemporaryFile(suffix='.json', mode="w+", delete=False) as mdata_file:
                try:
                    mdata_file.write(json.dumps(options))
                    mdata_file.flush()
                    mdata_file.close()
                    with setup.open('w+') as setup_file:
                        setup_file.write(f"""\
from vulcan.build_backend import setup
import json, pathlib
setup(**json.load(pathlib.Path(r'{mdata_file.name}').open()))
""")
                        yield
                finally:
                    os.unlink(mdata_file.name)
        finally:
            setup.unlink()
    else:
        yield


def install_develop() -> None:
    config = Vulcan.from_source(Path().absolute())

    try:
        virtual_env = get_virtualenv_python()
    except RuntimeError:
        exit('may not use vulcan develop outside of a virtualenv')

    with maybe_gen_setuppy(virtual_env, config):
        path = str(Path().absolute())
        if config.configured_extras:
            path = f'{path}[{",".join(config.configured_extras)}]'
        subprocess.check_call([
            str(virtual_env), '-m', 'pip', 'install', '-e', path])


# pep660 functions
def unpack(whl: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_output(f'wheel unpack {whl} -d {tmp}'.split())
        unpacked = list(Path(tmp).glob('*'))
        assert len(unpacked) == 1
        shutil.copytree(unpacked[0], whl.parent / unpacked[0].name)
        return whl.parent / unpacked[0].name


def pack(unpacked_wheel: Path) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_output(f'wheel pack {unpacked_wheel} -d {tmp}'.split())
        packed = list(Path(tmp).glob('*.whl'))
        assert len(packed) == 1
        shutil.copy(packed[0], unpacked_wheel.parent)
        return unpacked_wheel.parent / packed[0].name


def add_requirement(unpacked_whl_dir: Path, req: str) -> None:
    metadata = next(unpacked_whl_dir.glob('*.dist-info')) / 'METADATA'  # is mandatory
    with metadata.open() as f:
        metadata_lines = list(f)
    i = 0
    for i, line in enumerate(metadata_lines):
        if not (line.strip() and not line.startswith('Requires-Dist: ')):
            # find the start of the requires-dist, or the end of the metadata keys
            break
    metadata_lines.insert(i, f'Requires-Dist: {req}\n')
    metadata.write_text(''.join(metadata_lines))


def make_editable(whl: Path) -> None:
    config = Vulcan.from_source(Path().absolute())
    unpacked_whl_dir = unpack(whl)
    add_requirement(unpacked_whl_dir, f"editables (~={version('editables')})")
    # https://www.python.org/dev/peps/pep-0427/#escaping-and-unicode
    project_name = re.sub(r'[^\w\d.]+', '_', config.name, re.UNICODE)
    project = EditableProject(project_name, Path().absolute())
    for package in (config.packages or []):
        project.map(package, package)
        # removing the actual code packages because they will conflict with the .pth files, and take
        # precendence over them
        shutil.rmtree(unpacked_whl_dir / package)
    for name, content in project.files():
        (unpacked_whl_dir / name).write_text(content)

    assert whl == pack(unpacked_whl_dir), 'pre-wheel and post-wheel should be the same path'
    shutil.rmtree(unpacked_whl_dir)


def build_editable(wheel_directory: str, config_settings: Dict[str, str] = None,
                   metadata_directory: str = None) -> str:
    whl_path = Path(wheel_directory) / build_wheel(wheel_directory, config_settings, metadata_directory)
    make_editable(whl_path)
    return whl_path.name
