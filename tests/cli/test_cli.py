import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from click.testing import CliRunner, Result
from vulcan import Vulcan, cli


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
        assert 'Running!\n' == subprocess.check_output([output],
                                                       encoding='utf-8',
                                                       env={'SHIV_ROOT': str(tmp_path)})

    def test_shiv_add_works(self, runner: CliRunner, test_application: Path) -> None:
        config = Vulcan.from_source(test_application)
        assert 'switch-config-render' not in config.configured_dependencies
        with cd(test_application):
            successful(runner.invoke(cli.main, ['add', 'switch-config-render']))
        config = Vulcan.from_source(test_application)
        assert 'switch-config-render' in config.configured_dependencies


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
