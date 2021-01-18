from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional

__all__ = ['get_requires_for_build_sdist',
           'get_requires_for_build_wheel',
           'prepare_metadata_for_build_wheel',
           'build_wheel',
           'build_sdist']


def get_version() -> Optional[str]:
    try:
        with next(Path().rglob('VERSION')).open() as f:
            return f.read().strip() or None
    except StopIteration:
        return None


@contextmanager
def patch_version(version: str) -> Generator[None, None, None]:
    import toml
    with open('pyproject.toml') as f:
        old_config = f.read()
        config = toml.loads(old_config)
        config['tool']['poetry']['version'] = version
    with open('pyproject.toml', 'w+') as f:
        toml.dump(config, f)
    yield
    with open('pyproject.toml', 'w+') as f:
        f.write(old_config)


@contextmanager
def nullcontext() -> Generator[None, None, None]:
    yield

# For docs on the hooks: https://www.python.org/dev/peps/pep-0517/#build-backend-interface


def build_sdist(sdist_directory: str, config_settings: str = None) -> str:
    # just here to show that they are here
    import poetry.core.masonry.api as api  # type: ignore
    from vulcan.dist import SDist, gen_reqs
    desired_reqs = gen_reqs()
    version = get_version()
    pv = nullcontext()
    if version is not None:
        pv = patch_version(version)
    with open('poetry.lock') as f:
        lockfile = f.read()
    with pv:
        built_sdist = str(api.build_sdist(sdist_directory, config_settings))
        with SDist.unpack(Path(sdist_directory, built_sdist)) as sdist:
            sdist.fix_metadata(desired_reqs)
            # when poetry makes an sdist, it very helpfully removes the lockfile and adds a setup.py. This is
            # bad though, because the setup.py doesn't actually pin according to the lockfile
            # and so we remove the setup.py and add back the lockfile
            sdist.patch_lockfile(lockfile)
            sdist.remove_setuppy()
        return built_sdist


def build_wheel(wheel_directory: str, config_settings: str = None, metadata_directory: str = None
                ) -> str:
    import poetry.core.masonry.api as api
    from vulcan.dist import Wheel, gen_reqs
    desired_reqs = gen_reqs()
    version = get_version()
    pv = nullcontext()
    if version is not None:
        pv = patch_version(version)
    with pv:
        built_wheel = str(api.build_wheel(wheel_directory, config_settings, metadata_directory))
        with Wheel.unpack(Path(wheel_directory, built_wheel)) as wheel:
            wheel.fix_metadata(desired_reqs)
        return built_wheel


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings: str = None) -> str:
    import poetry.core.masonry.api as api
    version = get_version()
    pv = nullcontext()
    if version is not None:
        pv = patch_version(version)
    with pv:
        return str(api.prepare_metadata_for_build_wheel(metadata_directory, config_settings))


def get_requires_for_build_wheel(config_settings: str = None) -> List[str]:
    return ['wheel >= 0.36.2', 'poetry', 'setuptools', 'toml']


def get_requires_for_build_sdist(config_settings: str = None) -> List[str]:
    return ['poetry', 'setuptools', 'toml']
