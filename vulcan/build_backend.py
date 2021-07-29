import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, cast

import tomlkit
from editables import EditableProject  # type: ignore
from ppsetuptools.ppsetuptools import _parse_kwargs  # type: ignore

from vulcan import Vulcan, flatten_reqs
from vulcan.plugins import PluginRunner

# importing setuptools here rather than at point of use forces user to specify setuptools in their
# [build-system][requires] section
try:
    import setuptools  # type: ignore
except ImportError as e:
    raise ImportError(str(e) + '\nPlease add setuptools to [build-system] requires in pyproject.toml') from e


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
    return Path(virtual_env, 'bin', 'python')


# tox requires these two for some reason :(
def get_requires_for_build_sdist(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def get_requires_for_build_wheel(config_settings: Dict[str, str] = None) -> List[str]:
    return []


def install_develop() -> None:
    config = Vulcan.from_source(Path().absolute())

    try:
        virtual_env = get_virtualenv_python()
    except RuntimeError:
        exit('may not use vulcan develop outside of a virtualenv')

    if config.configured_extras:
        path = f'.[{",".join(config.configured_extras)}]'
    subprocess.check_call([
        virtual_env, '-m', 'pip', 'install', '-e', path])


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
    project = EditableProject(config.name, Path().absolute())
    for name, content in project.files():
        (unpacked_whl_dir / name).write_text(content)

    assert whl == pack(unpacked_whl_dir), 'pre-wheel and post-wheel should be the same path'
    shutil.rmtree(unpacked_whl_dir)


def build_editable(wheel_directory: str, config_settings: Dict[str, str] = None,
                   metadata_directory: str = None) -> str:
    whl_path = Path(wheel_directory) / build_wheel(wheel_directory, config_settings, metadata_directory)
    make_editable(whl_path)
    return whl_path.name
