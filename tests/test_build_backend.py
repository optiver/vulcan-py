import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from pkg_resources import Requirement
from vulcan import VulcanConfigError, to_pep508

import pytest
# it is NOT expected for these to fall out of date, unless you explicitly regenerate the test lockfile
# in tests/data
EXPECTED_REQS = {
            Requirement.parse('certifi==2020.12.5; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),  # noqa: E501
            Requirement.parse('chardet==4.0.0; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),  # noqa: E501
            Requirement.parse('idna==2.10; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),  # noqa: E501
            Requirement.parse('requests==2.25.1; (python_version >= "2.7" and python_full_version < "3.0.0") or python_full_version >= "3.5.0"'),  # noqa: E501
            Requirement.parse('urllib3==1.22; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"')}  # noqa: E501


@contextmanager
def cd(p: Path) -> Generator[None, None, None]:
    old = os.getcwd()
    os.chdir(p)
    yield
    os.chdir(old)


class TestFixturesOutput:
    """
    These tests are more for the fixtures than for anything in the library itself.
    """

    def test_built_sdist_final_output_format(self, built_sdist: Path) -> None:
        assert built_sdist.suffix == '.gz'

    def test_built_wheel_final_output_format(self, built_wheel: Path) -> None:
        assert built_wheel.suffix == '.whl'


class TestConfig:

    def test_pep508_simple(self) -> None:
        assert to_pep508('somelib', '~=1.2.3') == 'somelib~=1.2.3'

    def test_pep508_dict_no_extras(self) -> None:
        assert to_pep508('somelib', {'version': '~=1.2.3'}) == 'somelib~=1.2.3'

    def test_pep508_dict_extras(self) -> None:
        assert to_pep508('somelib', {'version': '~=1.2.3', 'extras': ['extra1', 'extra2']}
                         ) == 'somelib[extra1,extra2]~=1.2.3'

    def test_pep508_errors(self) -> None:
        with pytest.raises(VulcanConfigError, match="version"):
            # missing extras (optional) and version (mandatory)
            to_pep508('somelib', {})

        with pytest.raises(VulcanConfigError, match="version"):
            # missing version
            to_pep508('somelib', {'extras': ['someextra', 'anotherextra']})

        with pytest.raises(VulcanConfigError, match="must be a dict or a string"):
            # totally wrong type
            to_pep508('somelib', ['someextra', 'someextra2'])  # type: ignore
