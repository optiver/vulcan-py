from pathlib import Path

import pytest
from pkg_resources import Requirement
from pkginfo import Wheel  # type: ignore
from vulcan.builder import resolve_deps


@pytest.fixture
def wheel_pkg_info(test_built_application_wheel: Path) -> Wheel:
    return Wheel(str(test_built_application_wheel))


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
