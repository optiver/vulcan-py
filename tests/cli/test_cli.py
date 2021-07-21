import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner, Result
from vulcan import Vulcan, cli


@pytest.mark.cli
class BaseTestCli:

    @pytest.fixture
    def cli_test_application(self, _: Path) -> Path:
        raise NotImplementedError

    def test_lockfile_regen_idempotent(self, runner: CliRunner, cli_test_application: Path) -> None:

        with cd(cli_test_application):
            print(os.getcwd(), cli_test_application)
            successful(runner.invoke(cli.main, ['lock']))
        first_pass = (cli_test_application / 'vulcan.lock').read_text()

        with cd(cli_test_application):
            successful(runner.invoke(cli.main, ['lock']))
        assert (cli_test_application / 'vulcan.lock').read_text() == first_pass

    def test_shiv_build_works(self, runner: CliRunner, cli_test_application: Path, tmp_path: Path) -> None:
        with cd(cli_test_application):
            successful(runner.invoke(cli.main, ['build', '--shiv', '-o', 'dist']))
        output = cli_test_application / 'dist/testproject'
        assert output.exists()
        assert os.access(output, os.X_OK)
        assert 'Running!\n' == subprocess.check_output([output],
                                                       encoding='utf-8',
                                                       env={'SHIV_ROOT': str(tmp_path)})

    def test_shiv_add_works(self, runner: CliRunner, cli_test_application: Path) -> None:
        config = Vulcan.from_source(cli_test_application)
        assert 'switch-config-render' not in config.configured_dependencies
        with cd(cli_test_application):
            successful(runner.invoke(cli.main, ['add', 'switch-config-render']))
        config = Vulcan.from_source(cli_test_application)
        assert 'switch-config-render' in config.configured_dependencies


class TestCli(BaseTestCli):
    @pytest.fixture
    def cli_test_application(self, test_application: Path) -> Path:
        return test_application


class TestCliPep621(BaseTestCli):
    @pytest.fixture
    def cli_test_application(self, test_application_pep621: Path) -> Path:
        return test_application_pep621


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
    assert result.exit_code == 0
    return result
