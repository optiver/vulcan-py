import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from vulcan import cli


@contextmanager
def cd(p: Path) -> Generator[None, None, None]:
    old = os.getcwd()
    os.chdir(p)
    yield
    os.chdir(old)


@pytest.mark.cli
def test_lockfile_regen_idempotent(test_application: Path) -> None:

    with cd(test_application):
        cli.main(['lock'])
    first_pass = (test_application / 'vulcan.lock').read_text()

    with cd(test_application):
        cli.main(['lock'])
    assert (test_application / 'vulcan.lock').read_text() == first_pass


@pytest.mark.cli
def test_shiv_build_works(test_application: Path) -> None:
    with cd(test_application):
        cli.main(['build', '--shiv', '-o', 'dist'])
    output = test_application / 'dist/testproject'
    assert output.exists()
    assert os.access(output, os.X_OK)


@pytest.mark.cli
def test_lockfile_regen_idempotent_pep621(test_application_pep621: Path) -> None:

    with cd(test_application_pep621):
        cli.main(['lock'])
    first_pass = (test_application_pep621 / 'vulcan.lock').read_text()

    with cd(test_application_pep621):
        cli.main(['lock'])
    assert (test_application_pep621 / 'vulcan.lock').read_text() == first_pass


@pytest.mark.cli
def test_shiv_build_works_pep621(test_application_pep621: Path) -> None:
    with cd(test_application_pep621):
        cli.main(['build', '--shiv', '-o', 'dist'])
    output = test_application_pep621 / 'dist/testproject'
    assert output.exists()
    assert os.access(output, os.X_OK)
