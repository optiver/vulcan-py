import os
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import build
import pytest
from pkg_resources import Requirement
from vulcan import VulcanConfigError, to_pep508

from .conftest import build_dist

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

    def test_built_sdist_final_output_format_pep621(self, test_built_application_sdist_pep621: Path) -> None:
        assert test_built_application_sdist_pep621.suffix == '.gz'


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

    @pytest.mark.parametrize('mdata_file', ['METADATA', 'entry_points.txt'])
    def test_pep621_vulcan_equivilent(self, test_built_application_wheel: Path,
                                      test_built_application_wheel_pep621: Path, mdata_file: str) -> None:
        with zipfile.ZipFile(test_built_application_wheel) as old:
            with old.open(f'testproject-1.2.3.dist-info/{mdata_file}') as old_metadata:
                old_data = old_metadata.read().decode()

        with zipfile.ZipFile(test_built_application_wheel_pep621) as new:
            with new.open(f'testproject-1.2.3.dist-info/{mdata_file}') as new_metadata:
                new_data = new_metadata.read().decode()

        assert old_data == new_data

    def test_pep621_dependencies_key_forbidden(self,
                                               test_application_pep621_forbidden_keys: Path,
                                               tmp_path_factory: pytest.TempPathFactory) -> None:

        with pytest.raises(build.BuildBackendException):
            build_dist(test_application_pep621_forbidden_keys, 'wheel', tmp_path_factory.mktemp('build'))
