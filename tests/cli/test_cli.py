import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner, Result

from vulcan import Vulcan, cli
from vulcan.isolation import create_venv, get_executable


def versions_exist(*versions: str) -> bool:
    try:
        for v in versions:
            get_executable(v)
        return True
    except FileNotFoundError:
        return False


@pytest.mark.cli
class TestCli:

    def test_lockfile_regen_idempotent(self, runner: CliRunner, test_application: Path) -> None:

        with cd(test_application):
            print(os.getcwd(), test_application)
            successful(runner.invoke(cli.main, ['lock']))
        first_pass = (test_application / 'vulcan.lock').read_text()

        with cd(test_application):
            successful(runner.invoke(cli.main, ['lock']))
        assert (test_application / 'vulcan.lock').read_text() == first_pass

    def test_shiv_build_works(self, runner: CliRunner, test_application: Path, tmp_path: Path) -> None:
        with cd(test_application):
            successful(runner.invoke(cli.main, ['build', '--shiv', '-o', 'dist']))
        output = test_application / 'dist/testproject'
        assert output.exists()
        assert os.access(output, os.X_OK)
        if versions_exist('3.6'):
            # shebang there expects 3.6
            assert 'Running!\n' == subprocess.check_output([output], encoding='utf-8', env={'SHIV_ROOT': str(tmp_path)})

    def test_add_works_without_lockfile(self, runner: CliRunner, test_application: Path) -> None:
        (test_application / 'vulcan.lock').unlink()
        with cd(test_application):
            successful(runner.invoke(cli.main, ['add', 'switch-config-render']))
        config = Vulcan.from_source(test_application)
        assert 'switch-config-render' in config.configured_dependencies

    def test_add_works(self, runner: CliRunner, test_application: Path) -> None:
        config = Vulcan.from_source(test_application)
        assert 'switch-config-render' not in config.configured_dependencies
        with cd(test_application):
            successful(runner.invoke(cli.main, ['add', 'switch-config-render']))
        config = Vulcan.from_source(test_application)
        assert 'switch-config-render' in config.configured_dependencies

    def test_develop_works(self, runner: CliRunner, test_application: Path) -> None:
        with create_venv() as venv:
            successful(runner.invoke(cli.main, ['develop'], env={'VIRTUAL_ENV': venv.context.env_dir}))

    def test_lock_without_lockfile_succeeds(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            (test_application / 'vulcan.lock').unlink()
            successful(runner.invoke(cli.main, ['lock']))

    def test_build_without_lockfile_fails(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            (test_application / 'vulcan.lock').unlink()
            res = runner.invoke(cli.main, ['build', '--wheel'])
        assert res.exit_code != 0

    def test_develop_installs_all_dev_dependencies(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            res = runner.invoke(cli.main, ['develop'])
        assert 'pytest' in res.output
        assert 'flake8' in res.output

    def test_develop_test_installs_test_dev_dependencies(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            res = successful(runner.invoke(cli.main, ['develop', 'test']))
        assert 'pytest' in res.output
        assert 'flake8' not in res.output

    def test_develop_lint_installs_lint_dev_dependencies(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            res = successful(runner.invoke(cli.main, ['develop', 'lint']))
        assert 'pytest' not in res.output
        assert 'flake8' in res.output

    def test_develop_fake_errors(self, runner: CliRunner, test_application: Path) -> None:
        with cd(test_application):
            res = runner.invoke(cli.main, ['develop', 'faketarget'])
        assert res.exit_code != 0
        assert 'No such dev dependency' in res.output


@contextmanager
def cd(p: Path) -> Generator[None, None, None]:
    old = os.getcwd()
    os.chdir(p)
    yield
    os.chdir(old)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def successful(result: Result) -> Result:
    assert result.exit_code == 0, f'{result.stdout}'
    return result
