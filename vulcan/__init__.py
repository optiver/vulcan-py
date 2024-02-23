from __future__ import annotations

import distutils.core
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TypedDict, Union, cast

import tomlkit
import tomlkit.container
import tomlkit.items
from setuptools import setup


class VulcanConfigError(Exception):
    pass


class VersionDict(TypedDict, total=False):
    version: str
    extras: list[str]


VersionSpecs = Mapping[str, Union[str, VersionDict]]


def flatten_reqs(versions: VersionSpecs) -> list[str]:
    return [to_pep508(lib, req) for lib, req in versions.items()]


def list_or_none(val: Any) -> list[str] | None:
    return [str(v) for v in val] if val is not None else None


def str_or_none(val: Any) -> str | None:
    return str(val) if val is not None else None


def dict_or_none(val: Any) -> dict[str, Any] | None:
    return {str(k): v for k, v in val.items()} if val is not None else None


@dataclass
class Vulcan:
    source_path: Path
    plugins: list[str] | None
    lockfile: Path
    dependencies: list[str] | None
    configured_dependencies: VersionSpecs
    extras: dict[str, list[str]] | None
    configured_extras: dict[str, list[str]]
    dynamic: list[str] | None
    no_lock: bool = False
    python_lock_with: str | None = None

    @classmethod
    def from_source(cls, source_path: Path, fail_on_missing_lock: bool = True) -> "Vulcan":
        content = (source_path / "pyproject.toml").read_text()
        all_config = tomlkit.loads(content)
        config = all_config["tool"]["vulcan"]  # type: ignore[index]
        assert isinstance(config, dict)
        dynamic = all_config["project"].get("dynamic", [])  # type: ignore[union-attr]
        lockfile = source_path / config.get("lockfile", "vulcan.lock")

        no_lock = config.get("no-lock", False)
        install_requires: list[str] | None = None
        extras_require: dict[str, list[str]] | None = {}
        if not no_lock:
            try:
                install_requires, extras_require = get_requires(lockfile)
            except FileNotFoundError:
                if fail_on_missing_lock:
                    raise
                install_requires = None
                extras_require = None

        python_lock_with = config.get("python-lock-with")

        if "dev-dependencies" in config:
            print(
                "ERROR: tool.vulcan.dev-dependencies is not supported since 3.0.0, please use extras instead.",
                file=sys.stderr,
            )
            exit(1)

        shiv_config = config.get("shiv", [])
        if shiv_config:
            print("shiv configuration is not supported since 3.0.0.", file=sys.stderr)
            exit(1)

        # note that setuptools also checks this, and says that it _should_ consider this a warning, but will
        # not for the intermediate period.
        # We'll consider it an error until setuptools sees fit to do it for us, and then remove this check.
        if "dependencies" in config and "dependencies" not in dynamic:
            raise RuntimeError(
                "tool.vulcan.dependencies configured but 'dependencies' not in dynamic,"
                " this is an error according to PEP-621. "
                "See https://peps.python.org/pep-0621/#dynamic for more information"
            )
        if "extras" in config and "optional-dependencies" not in dynamic:
            raise RuntimeError(
                "tool.vulcan.extras configured but 'optional-dependencies' not in dynamic,"
                " this is an error according to PEP-621. "
                "See https://peps.python.org/pep-0621/#dynamic for more information"
            )

        return cls(
            source_path=source_path,
            plugins=list_or_none(config.get("plugins")),
            lockfile=lockfile,
            dependencies=install_requires,
            configured_dependencies=config.get("dependencies", {}),
            extras=extras_require,
            configured_extras=config.get("extras", {}),
            no_lock=no_lock,
            python_lock_with=python_lock_with,
            dynamic=dynamic,
        )

    def setup(self, config_settings: dict[str, str] | None = None) -> distutils.core.Distribution:
        install_requires: list[str] | None
        extras_require: dict[str, list[str]] | None
        if self.no_lock or (config_settings and config_settings.get("no-lock") == "true"):
            install_requires = flatten_reqs(self.configured_dependencies)
            extras_require = self.configured_extras
        else:
            install_requires = self.dependencies
            extras_require = self.extras
        # setuptools apparently does not know what setuptools returns
        # very reassuring
        return setup(  # type: ignore[no-any-return,func-returns-value]
            install_requires=install_requires, extras_require=extras_require
        )


def get_requires(lockfile: Path) -> tuple[list[str], dict[str, list[str]]]:
    if not lockfile.exists():
        raise FileNotFoundError(f"Expected lockfile {lockfile}, does not exist")
    with lockfile.open() as f:
        content = cast(tomlkit.container.Container, tomlkit.loads(f.read()))

    return (
        list(content["install_requires"]),  # type: ignore
        {k: list(v) for k, v in cast(tomlkit.container.Container, content["extras_require"]).items()},
    )


def to_pep508(lib: str, req: Union[str, VersionDict]) -> str:
    if not isinstance(req, (str, dict)):
        raise VulcanConfigError(f"Invalid requirement {req} -- must be a dict or a string")
    if isinstance(req, str):
        # e.g. "example_lib", "~=1.2.3" -> "example_lib~=1.2.3"
        return f"{lib}{req}"
    try:
        extras = f'[{",".join(req["extras"])}]' if "extras" in req else ""
        # "example_lib", {"version": "~=1.2.3", "extras"=["networkx","git"]}
        #                           -> "example_lib[networkx,git]~=1.2.3"
        # "example_lib", {"version": "~=1.2.3"} -> "example_lib~=1.2.3"
        return f'{lib}{extras}{req["version"]}'
    except KeyError as e:
        raise VulcanConfigError(f"invalid requirement {lib} ({req}) -- {e}") from e
