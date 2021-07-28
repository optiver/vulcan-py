import os
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest
from pkg_resources import Requirement
from pkginfo import Wheel  # type: ignore
from vulcan import VulcanConfigError, to_pep508

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

    def test_dependencies_key_forbidden(self,
                                        test_built_application_wheel: Path,
                                        tmp_path_factory: pytest.TempPathFactory) -> None:

        pass


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

    @pytest.mark.parametrize('mdata_file',
                             ['METADATA',
                              'entry_points.txt',
                              'RECORD',
                              'top_level.txt',
                              'WHEEL'])
    def test_metadata_files_exist_not_empty(self, test_built_application_wheel: Path,
                                            mdata_file: str) -> None:
        with zipfile.ZipFile(test_built_application_wheel) as new:
            with new.open(f'testproject-1.2.3.dist-info/{mdata_file}') as new_metadata:
                assert new_metadata.read().decode()

    def test_plugin_generated_file_exists(self, test_built_application_wheel: Path) -> None:
        with zipfile.ZipFile(test_built_application_wheel) as whl:
            with whl.open('testproject/example.no-hash.py') as nohash:
                assert nohash.read() == b'Text!'

    def test_lockfile_reqs_present(self, test_application: Path, test_built_application_wheel: Path) -> None:
        whl = Wheel(test_built_application_wheel)
        assert whl.requires_dist, "No dependencies found"
        assert any("; extra == 'test1'" in req for req in whl.requires_dist), "no extra dependencies found"


def test_editable_install(test_application: Path) -> None:
    assert False, "pip cannot yet do its part in this, see https://github.com/pypa/pip/pull/8212"
