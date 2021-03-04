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