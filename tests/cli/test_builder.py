import subprocess
from pathlib import Path
from typing import Tuple

import pytest
from pkg_resources import Requirement
from pkginfo import Wheel  # type: ignore
from vulcan.builder import resolve_deps
from vulcan.isolation import get_executable


@pytest.fixture
def wheel_pkg_info(test_built_application_wheel: Path) -> Wheel:
    return Wheel(str(test_built_application_wheel))


def versions_exist(*versions: str) -> bool:
    try:
        for v in versions:
            get_executable(v)
        return True
    except subprocess.CalledProcessError:
        return False


class TestResolveDeps:
    """
    These tests are more for the fixtures than for anything in the library itself.
    """

    def test_resolve_deps_no_conflict(self, wheel_pkg_info: Wheel) -> None:
        reqs = [Requirement.parse(reqstring) for reqstring in wheel_pkg_info.requires_dist]
        assert len({req.name for req in reqs}) == len({(req.name, req.specifier) for req in reqs}), 'duplicate package found in requirements'  # type: ignore # noqa: E501

    def test_empty_reqs_empty_deps(self) -> None:
        assert resolve_deps([], {}) == ([], {})

    def test_empty_base_non_empty_extras_empty_base(self) -> None:
        base, extras = resolve_deps([], {'test': ['requests']})
        assert base == []
        assert extras

    def test_non_empty_base_empty_extras_empty_extras(self) -> None:
        base, extras = resolve_deps(['requests'], {})
        assert base
        assert extras == {}

    def test_same_reqs_same_deps(self) -> None:
        base, extras = resolve_deps(['requests'], {'test': ['requests']})
        # output should be sorted, so it is good to just test equality here
        assert base == extras['test']

    def test_conflicting_deps_raises(self) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            resolve_deps(['requests==2.5.0'], {'test': ['requests==2.4.0']})

    @pytest.mark.skipif(not versions_exist('3.6', '3.4'), reason='missing python version for test')
    def test_resolve_different_python_versions(self) -> None:
        spec = 'options-sdk>=4.0.1,<=5.0.0'
        resolved, _ = resolve_deps([spec], {}, python_version='3.6')
        print(resolved)
        assert 'options-sdk==5.0.0' in resolved
        resolved, _ = resolve_deps([spec], {}, python_version='3.4')
        print(resolved)
        assert 'options-sdk==4.0.1' in resolved
