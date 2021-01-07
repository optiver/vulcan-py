import hashlib
from pathlib import Path
from typing import Dict

import build
import pytest
import shutil


def hashes(directory: Path) -> Dict[Path, str]:
    hs = {}
    for file in directory.rglob('*'):
        if str(file).startswith('.'):
            continue
        if '.egg-info' in str(file):
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


@pytest.fixture
def built_sdist(tmp_path: Path) -> Path:
    dist_dir = (tmp_path / 'dist').absolute()
    return build_dist(Path(), 'sdist', dist_dir)


@pytest.fixture
def built_wheel(tmp_path: Path) -> Path:
    dist_dir = (tmp_path / 'dist').absolute()
    return build_dist(Path(), 'wheel', dist_dir)


# shouldn't need to do this IMO
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
    (tmp_path / 'testproject/__init__.py').touch()
    test_lockfile = (Path(__file__).parent / 'data/test_application_poetry.lock')
    shutil.copy(test_lockfile, tmp_path / 'poetry.lock')
    with (tmp_path / 'pyproject.toml').open('w+') as f:
        f.write("""\
[tool.poetry]
name = "testproject"
version = "1.2.3"
description = "an example test project for testing vulcan builds"
authors = ["Joel Christiansen <joelchristiansen@optiver.com>"]
packages = [ { include="testpkg" } ]
keywords = [ "build", "testing" ]
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
    ]

[tool.poetry.dependencies]
python = ">=3.6"
requests = "^2.25.1"

[[tool.poetry.source]]
# semi-mandatory, needed for poetry but doesn't help with pip. Not super nice.
name = "optiver"
url = "http://artifactory.ams.optiver.com/artifactory/api/pypi/pypi/simple"
default = true

[build-system]
requires=['setuptools', 'vulcan']
build-backend="vulcan.build_backend"

[tool.poetry.scripts]
myep = "vulcan.test_ep:main"
""")

    return tmp_path


@pytest.fixture(scope='session')
def test_built_application(test_application: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_dist(test_application, 'sdist', tmp_path_factory.mktemp('build'))

@pytest.fixture(scope='session')
def test_built_application_wheel(test_application: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_dist(test_application, 'wheel', tmp_path_factory.mktemp('build'))
