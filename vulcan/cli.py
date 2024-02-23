from __future__ import annotations

import asyncio
import asyncio.subprocess
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import build.env
import click
import packaging.version
import tomlkit
from pkg_resources import Requirement

import build
from vulcan import Vulcan, flatten_reqs
from vulcan.build_backend import get_virtualenv_python
from vulcan.builder import resolve_deps

pass_vulcan = click.make_pass_decorator(Vulcan)

try:
    vulcan_version = version("vulcan-py")
except PackageNotFoundError:
    vulcan_version = "0.0.0"


@click.group()
@click.version_option(vulcan_version)
@click.pass_context
def main(ctx: click.Context) -> None:
    # don't fail on missing lock here, because this config object is not actually used for building only for
    # cli values
    ctx.obj = Vulcan.from_source(Path().absolute(), fail_on_missing_lock=False)


@main.command(name="build")
@click.option("--outdir", "-o", default="dist/", type=Path)
@click.option("--lock/--no-lock", "_lock", default=True)
@click.option("--wheel", is_flag=True, default=False)
@click.option("--sdist", is_flag=True, default=False)
@pass_vulcan
def build_out(_: Vulcan, outdir: Path, _lock: bool, wheel: bool, sdist: bool) -> None:
    "Create wheels, and sdists"
    # for ease of use
    if len([v for v in (wheel, sdist) if v]) != 1:
        raise click.UsageError("Must specify exactly 1 of --wheel, or --sdist")

    config_settings = {}
    if not _lock:
        config_settings["no-lock"] = "true"
    project = build.ProjectBuilder(".")
    outdir.mkdir(exist_ok=True)
    if sdist:
        project.build("sdist", str(outdir), config_settings=config_settings)
    elif wheel:
        project.build("wheel", str(outdir), config_settings=config_settings)
    else:
        assert False, "unreachable because dist_types is required"


async def resolve_deps_or_report(
    config: Vulcan, python_version: str | None = None
) -> tuple[list[str], dict[str, list[str]]]:
    try:
        return await resolve_deps(
            flatten_reqs(config.configured_dependencies),
            config.configured_extras or {},
            python_version,
        )

    except subprocess.CalledProcessError as e:
        print(e.stderr.decode(), file=sys.stderr)
        raise


@main.command()
@pass_vulcan
def lock(config: Vulcan) -> None:
    "Generate and update lockfile"

    python_version = config.python_lock_with
    # this check does not make sense on windows as far as I can tell,
    # there is never a "python3.6" or "python2.7" binary just "python"
    if python_version is None and sys.platform != "win32":
        try:
            # default to configured lock value, then current venv value if it exists, fallback to vulcan's
            # version
            python = get_virtualenv_python()
            python_version = subprocess.check_output(
                [
                    str(python),
                    "-c",
                    'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")',
                ],
                encoding="utf-8",
            ).strip()

        except RuntimeError:
            pass
    install_requires, extras_require = asyncio.get_event_loop().run_until_complete(
        resolve_deps_or_report(config, python_version)
    )
    doc = tomlkit.document()
    doc["install_requires"] = tomlkit.array(install_requires).multiline(True)  # type: ignore
    doc["extras_require"] = {k: tomlkit.array(v).multiline(True) for k, v in extras_require.items()}  # type: ignore
    with open(config.lockfile, "w+") as f:
        f.write(tomlkit.dumps(doc))


@main.command()
@click.argument("req", type=Requirement.parse)
@click.option("--lock/--no-lock", "_lock", default=True)
@pass_vulcan  # order matters, closest to the function definition comes first
@click.pass_context
def add(ctx: click.Context, config: Vulcan, req: Requirement, _lock: bool) -> None:
    "Add new top-level dependency and regenerate lockfile"
    name: str = req.name
    if req.extras:
        name = f'{name}[{",".join(req.extras)}]'
    try:
        venv_python = get_virtualenv_python()
    except RuntimeError:
        exit("Must be in a virtualenv to use `vulcan add`")
    subprocess.check_call([str(venv_python), "-m", "pip", "install", str(req)])
    if req.specifier:
        # if the user gave a version spec, we blindly take that
        version = str(req.specifier)
    else:
        # otherwise, we take a freeze to see what was actually installed
        freeze = subprocess.check_output([str(venv_python), "-m", "pip", "freeze"], encoding="utf-8").strip()
        try:
            # try and find the thing we just added
            line = next(ln for ln in freeze.split("\n") if ln.startswith(req.name))
            # and parse it to a version
            spec = packaging.version.parse(
                str(Requirement.parse(line.strip()).specifier)[2:]
            )  # remove the == at the start
            version = f"~={spec.major}.{spec.minor}"
        except StopIteration:
            # failed to find the thing we just installed, give up.
            version = ""
    with open("pyproject.toml") as f:
        parse = tomlkit.parse(f.read())
    deps = parse["tool"]["vulcan"].setdefault("dependencies", tomlkit.table())  # type: ignore
    deps[name] = version
    with open("pyproject.toml", "w+") as f:
        f.write(tomlkit.dumps(parse))
    if not config.no_lock and _lock:
        ctx.obj = Vulcan.from_source(Path().absolute(), fail_on_missing_lock=False)
        ctx.invoke(lock)


if __name__ == "__main__":
    main()
