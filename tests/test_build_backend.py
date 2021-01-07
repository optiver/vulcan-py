import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pkginfo  # type: ignore
import pytest
import vulcan.options
from pkg_resources import Requirement


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


class TestMetadata:
    # Testing that all metadata gets translated as expected
    @pytest.fixture(scope='class')
    def metadata(self, test_built_application: Path) -> pkginfo.SDist:
        return pkginfo.SDist(test_built_application)

    def test_author(self, metadata: pkginfo.Wheel) -> None:
        assert metadata.author == 'Joel Christiansen'
        assert metadata.author_email == 'joelchristiansen@optiver.com'

    def test_name(self, metadata: pkginfo.Wheel) -> None:
        assert metadata.name == 'testproject'

    def test_version_exists(self, metadata: pkginfo.Wheel) -> None:
        assert metadata.version

    def test_requirements(self, metadata: pkginfo.Wheel) -> None:
        from pprint import pprint
        pprint(metadata.__dict__)
        assert not metadata.install_requires


class TestOptions:
    def test_gen_reqs(self, test_application: Path) -> None:
        expected_reqs = {
            Requirement.parse('certifi==2020.12.5; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),
            Requirement.parse('chardet==4.0.0; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),
            Requirement.parse('idna==2.10; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"'),
            Requirement.parse('requests==2.25.1; (python_version >= "2.7" and python_full_version < "3.0.0") or python_full_version >= "3.5.0"'),
            Requirement.parse('urllib3==1.22; python_version >= "2.7" and python_full_version < "3.0.0" or python_full_version >= "3.5.0"')}
        with cd(test_application):
            reqs = vulcan.options.gen_reqs()
            assert set(reqs) == expected_reqs
