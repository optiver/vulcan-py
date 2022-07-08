import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from pkg_resources import Requirement
from pkginfo import Wheel

from vulcan.builder import resolve_deps
from vulcan.isolation import get_executable


@contextmanager
def verbose_called_process_error() -> Iterator[None]:
    try:
        yield
    except subprocess.CalledProcessError as err:
        print(err.stdout)
        print(err.stderr, file=sys.stderr)
        raise


@pytest.fixture
def wheel_pkg_info(test_built_application_wheel: Path) -> Wheel:
    return Wheel(str(test_built_application_wheel))


def versions_exist(*versions: str) -> bool:
    try:
        for v in versions:
            get_executable(v)
        return True
    except FileNotFoundError:
        return False


class TestResolveDeps:
    """
    These tests are more for the fixtures than for anything in the library itself.
    """

    def test_resolve_deps_no_conflict(self, wheel_pkg_info: Wheel) -> None:
        reqs = [Requirement.parse(reqstring) for reqstring in wheel_pkg_info.requires_dist]
        assert len({req.name for req in reqs}) == len({(req.name, req.specifier) for req in reqs}), 'duplicate package found in requirements'  # type: ignore # noqa: E501

    @pytest.mark.asyncio
    async def test_empty_reqs_empty_deps(self) -> None:
        with verbose_called_process_error():
            assert await resolve_deps([], {}) == ([], {})

    @pytest.mark.asyncio
    async def test_empty_base_non_empty_extras_empty_base(self) -> None:
        with verbose_called_process_error():
            base, extras = await resolve_deps([], {'test': ['requests']})
        assert base == []
        assert extras

    @pytest.mark.asyncio
    async def test_non_empty_base_empty_extras_empty_extras(self) -> None:
        with verbose_called_process_error():
            base, extras = await resolve_deps(['requests'], {})
        assert base
        assert extras == {}

    @pytest.mark.asyncio
    async def test_same_reqs_same_deps(self) -> None:
        with verbose_called_process_error():
            base, extras = await resolve_deps(['requests'], {'test': ['requests']})
        # output should be sorted, so it is good to just test equality here
        assert base == extras['test']

    @pytest.mark.asyncio
    async def test_conflicting_deps_raises(self) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            await resolve_deps(['requests==2.5.0'], {'test': ['requests==2.4.0']})

    @pytest.mark.skipif(not versions_exist('3.6', '3.9'), reason='missing python version for test')
    @pytest.mark.asyncio
    async def test_resolve_different_python_versions(self) -> None:
        spec = 'traitlets>=4.0.1,<=5.0.5'
        with verbose_called_process_error():
            resolved, _ = await resolve_deps([spec], {}, python_version='3.6')
        print(resolved)
        assert 'traitlets==4.3.3' in resolved
        with verbose_called_process_error():
            resolved, _ = await resolve_deps([spec], {}, python_version='3.9')
        print(resolved)
        assert 'traitlets==5.0.5' in resolved
