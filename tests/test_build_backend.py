import os
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from zipfile import ZipFile

import pkginfo  # type: ignore
import pytest
import vulcan.options
from pkg_resources import Requirement

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


class TestMetadata:
    # Testing that all metadata gets translated as expected
    @pytest.fixture(scope='class')
    def wheel_metadata(self, test_built_application_wheel: Path) -> pkginfo.Wheel:
        return pkginfo.Wheel(test_built_application_wheel)

    @pytest.fixture(scope='class')
    def sdist_metadata(self, test_built_application: Path) -> pkginfo.SDist:
        return pkginfo.SDist(test_built_application)

    def test_author(self, wheel_metadata: pkginfo.Wheel, sdist_metadata: pkginfo.SDist) -> None:
        assert wheel_metadata.author == sdist_metadata.author == 'Joel Christiansen'
        assert wheel_metadata.author_email == sdist_metadata.author_email == 'joelchristiansen@optiver.com'

    def test_name(self, wheel_metadata: pkginfo.Wheel, sdist_metadata: pkginfo.SDist) -> None:
        assert wheel_metadata.name == sdist_metadata.name == 'testproject'

    def test_version_exists(self, wheel_metadata: pkginfo.Wheel, sdist_metadata: pkginfo.SDist) -> None:
        assert (wheel_metadata.version == sdist_metadata.version) and wheel_metadata.version

    def test_version_from_VERSION_file(self, wheel_metadata: pkginfo.Wheel,
                                       sdist_metadata: pkginfo.SDist) -> None:
        assert wheel_metadata.version == '1.2.3'

    def test_requirements(self, wheel_metadata: pkginfo.Wheel, sdist_metadata: pkginfo.SDist) -> None:
        # This is a "bug" in setuptools, see: https://github.com/pypa/setuptools/issues/1716
        # if this test fails with an error that looks like "5 != 0", delete the below 2 lines and uncomment
        # the third, as that will mean the bug has been fixed.
        assert len(sdist_metadata.requires_dist) == 0, \
            "It is unexpected to correctly parse sdist requirements, see comment"
        assert len(wheel_metadata.requires_dist) == 5
        assert {Requirement.parse(spec) for spec in wheel_metadata.requires_dist} == EXPECTED_REQS
        # assert len(sdist_metadata.requires_dist) == len(wheel_metadata.requires_dist) == 5

    def test_python_requires(self, wheel_metadata: pkginfo.Wheel, sdist_metadata: pkginfo.SDist) -> None:
        assert wheel_metadata.requires_python == sdist_metadata.requires_python == '>=3.6'

    def test_entry_points(self, test_built_application_wheel: Path, wheel_metadata: pkginfo.Wheel) -> None:
        with ZipFile(test_built_application_wheel) as zf:
            config = ConfigParser(interpolation=None)
            with zf.open(f'{wheel_metadata.name}-{wheel_metadata.version}.dist-info/entry_points.txt') as eps:
                config.read_string(eps.read().decode())

        assert {s: dict(o.items()) for s, o in config.items() if s != 'DEFAULT'} == {
            'console_scripts': {'myep': 'vulcan.test_ep:main'},
            'testplugin': {'someplugin': 'some.import:spec'}}


class TestOptions:
    def test_gen_reqs(self, test_application: Path) -> None:
        with cd(test_application):
            reqs = vulcan.options.gen_reqs()
            assert set(reqs) == EXPECTED_REQS
