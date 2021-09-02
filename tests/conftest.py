import hashlib
import shutil
from pathlib import Path
from typing import Dict, Generator
from contextlib import contextmanager
import os
import sys

import build
import pytest
from pkginfo import Wheel  # type: ignore


@contextmanager
def cd(p: Path) -> Generator[None, None, None]:
    old = os.getcwd()
    os.chdir(p)
    yield
    os.chdir(old)


def hashes(directory: Path) -> Dict[Path, str]:
    hs = {}
    for file in directory.rglob('*'):
        if str(file).startswith('.'):
            continue
        if '.egg-info' in str(file):
            continue
        if 'build' in file.parts:
            continue
        if 'dist' in file.parts:
            continue
        if 'no-hash' in str(file):
            continue
        if not file.is_file():
            continue
        with file.open('rb') as f:
            hs[file] = hashlib.md5(f.read()).hexdigest()
    return hs


def build_dist(source: Path, dist_type: str, target: Path) -> Path:
    assert dist_type in ('sdist', 'wheel')
    hashes_pre = hashes(source)
    project = build.ProjectBuilder(str(source.absolute()))
    # docs for this project _say_ that build returns the path to the built artifact, but that appears to be
    # not actually true
    project.build(dist_type, str(target.absolute()))
    if dist_type == 'sdist':
        built = next(target.glob('*.gz'))
    else:
        built = next(target.glob('*.whl'))
    assert hashes_pre == hashes(
        source), 'cwd not clean after build, ensure the build script cleans up any generated files'
    return Path(built)


@pytest.fixture(autouse=True)
def _preserve_lockfile(test_application: Path) -> Generator[None, None, None]:
    old_content = (test_application / 'vulcan.lock').read_text()
    yield
    (test_application / 'vulcan.lock').write_text(old_content)


@pytest.fixture
def built_sdist(tmp_path: Path) -> Path:
    dist_dir = (tmp_path / 'dist').absolute()
    return build_dist(Path(), 'sdist', dist_dir)


@pytest.fixture
def built_wheel(tmp_path: Path) -> Path:
    dist_dir = (tmp_path / 'dist').absolute()
    return build_dist(Path(), 'wheel', dist_dir)


@pytest.fixture(scope='class')
def class_built_sdist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dist_dir = (tmp_path_factory.mktemp('build') / 'dist').absolute()
    return build_dist(Path(), 'sdist', dist_dir)


@pytest.fixture(scope='class')
def class_built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dist_dir = (tmp_path_factory.mktemp('build') / 'dist').absolute()
    return build_dist(Path(), 'wheel', dist_dir)


@pytest.fixture(scope='session')
def test_application(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp('build_testproject')
    (tmp_path / 'testproject').mkdir()
    (tmp_path / 'testproject/__init__.py').write_text("""\
def test_ep():
    print("Running!")
""")
    with (tmp_path / 'testproject/VERSION').open('w+') as f:
        f.write('1.2.3\n')
    test_lockfile = (Path(__file__).parent / 'data/test_application_vulcan.lock')
    shutil.copy(test_lockfile, tmp_path / 'vulcan.lock')
    with (tmp_path / 'pyproject.toml').open('w+') as f:
        f.write("""\
[project]
name = "testproject"
description = "an example test project for testing vulcan builds, %"
authors = [{{name="Joel Christiansen", email="joelchristiansen@optiver.com"}}]
keywords = [ "build", "testing" ]
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
    ]
requires-python = ">=3.6"

[project.scripts]
myep = "testproject:test_ep"

[tool.vulcan.plugin.example_plugin]
foobar = "barfoo"
module_dir = "testproject"


[project.entry-points.test_eps]
myep = "testproject:test_ep"

[tool.vulcan]
packages = [ "testproject" ]
plugins = ['example_plugin']

[tool.vulcan.dependencies]
requests = {{version="~=2.25.1", extras=["security"]}}

[tool.vulcan.extras]
test1 = ["requests", "build"]
test2 = ["requests~=2.22", "setuptools"]
test3 = ["requests>=2.0.0", "wheel"]

[[tool.vulcan.shiv]]
bin_name="testproject"
console_script="myep"
interpreter='{cur_interp}'
extra_args="-E --compile-pyc"


[build-system]
requires=['setuptools', 'vulcan-py']
build-backend="vulcan.build_backend"

""".format(cur_interp=sys.executable))

    return tmp_path


@pytest.fixture(scope='session')
def test_application_forbidden_keys(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp('build_testproject')
    (tmp_path / 'testproject').mkdir()
    (tmp_path / 'testproject/__init__.py').write_text("""\
def test_ep():
    print("Running!")
""")
    with (tmp_path / 'testproject/VERSION').open('w+') as f:
        f.write('1.2.3\n')
    test_lockfile = (Path(__file__).parent / 'data/test_application_vulcan.lock')
    shutil.copy(test_lockfile, tmp_path / 'vulcan.lock')
    with (tmp_path / 'pyproject.toml').open('w+') as f:
        f.write("""\
[project]
name = "testproject"
description = "an example test project for testing vulcan builds, %"
authors = [{{name="Joel Christiansen", email="joelchristiansen@optiver.com"}}]
keywords = [ "build", "testing" ]
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
    ]
requires-python = ">=3.6"

[project.scripts]
myep = "testproject:test_ep"

[tool.vulcan.plugin.example_plugin]
foobar = "barfoo"
module_dir = "testproject"


[project.entry-points.test_eps]
myep = "testproject:test_ep"

[tool.vulcan]
packages = [ "testproject" ]
plugins = ['example_plugin']

[tool.vulcan.dependencies]
requests = {{version="~=2.25.1", extras=["security"]}}

[tool.vulcan.extras]
test1 = ["requests", "build"]
test2 = ["requests~=2.22", "setuptools"]
test3 = ["requests>=2.0.0", "wheel"]

[[tool.vulcan.shiv]]
bin_name="testproject"
console_script="myep"
interpreter='{cur_interp}'
extra_args="-E --compile-pyc"


[build-system]
requires=['setuptools', 'vulcan-py']
build-backend="vulcan.build_backend"

""".format(cur_interp=sys.executable))

    return tmp_path


@pytest.fixture(scope='session')
def test_built_application(
        test_application: Path,
        tmp_path_factory: pytest.TempPathFactory) -> Path:
    with cd(test_application):
        sdist = build_dist(test_application, 'sdist', tmp_path_factory.mktemp('build'))
    return sdist


@pytest.fixture(scope='session')
def test_built_application_wheel(test_application: Path,
                                 tmp_path_factory: pytest.TempPathFactory) -> Path:
    with cd(test_application):
        whl = build_dist(test_application, 'wheel', tmp_path_factory.mktemp('build'))
    return whl


@ pytest.fixture(scope='session')
def wheel_pkg_info(test_built_application_wheel: Path) -> Wheel:
    return Wheel(str(test_built_application_wheel))
