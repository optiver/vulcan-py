import asyncio
import asyncio.subprocess
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import build.env
import click
import packaging.version
import tomlkit
from pkg_resources import Requirement

import build
from vulcan import Vulcan, flatten_reqs
from vulcan.build_backend import (get_pip_version, get_virtualenv_python,
                                  install_develop)
from vulcan.builder import resolve_deps

version: Callable[[str], str]
if sys.version_info >= (3, 8):
    from importlib.metadata import PackageNotFoundError, version
else:
    from importlib_metadata import PackageNotFoundError, version

pass_vulcan = click.make_pass_decorator(Vulcan)

try:
    vulcan_version = version('vulcan-py')
except PackageNotFoundError:
    vulcan_version = '0.0.0'


@click.group()
@click.version_option(vulcan_version)
@click.pass_context
def main(ctx: click.Context) -> None:
    if sys.platform == 'win32':
        # This is required for python <3.8, where this is not yet the default for windows.
        # Can be removed when support for those are removed.
        # https://docs.python.org/3.7/library/asyncio-eventloop.html#event-loop-implementations
        #
        # > By default asyncio is configured to use SelectorEventLoop on all platforms.
        #
        # And then https://docs.python.org/3.8/library/asyncio-eventloop.html#event-loop-implementations
        #
        # > By default asyncio is configured to use SelectorEventLoop on Unix and ProactorEventLoop on
        #   Windows.
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    # don't fail on missing lock here, because this config object is not actually used for building only for
    # cli values
    ctx.obj = Vulcan.from_source(Path().absolute(), fail_on_missing_lock=False)


async def build_shiv_apps(from_dist: str, vulcan: Vulcan, outdir: Path) -> List[Path]:
    results = []
    for app in vulcan.shiv_options:
        try:
            if app.with_extras:
                dist = f'{from_dist}[{",".join(app.with_extras)}]'
            else:
                dist = from_dist
            cmd = [sys.executable, '-m', 'shiv', dist, '-o', str(outdir / app.bin_name)]
            if app.console_script:
                cmd += ['-c', app.console_script]
            if app.entry_point:
                cmd += ['-e', app.entry_point]
            if app.interpreter:
                cmd += ['-p', app.interpreter]
            if app.extra_args:
                cmd += shlex.split(app.extra_args)
            proc = await asyncio.subprocess.create_subprocess_exec(*cmd)
            results.append((proc, app.bin_name))
        except KeyError as e:
            raise KeyError('missing config value in pyproject.toml: {e}') from e
    await asyncio.gather(*(p.wait() for p, _ in results))
    succeeded = []
    failed = []
    for proc, res in results:
        if await proc.wait() == 0:
            succeeded.append(outdir / res)
        else:
            failed.append(res)
    for fail in failed:
        print(f"failed to create executable {failed}", file=sys.stderr)
    return succeeded


@main.command(name='build')
@click.option('--outdir', '-o', default='dist/', type=Path)
@click.option('--lock/--no-lock', '_lock', default=True)
@click.option('--wheel', is_flag=True, default=False)
@click.option('--sdist', is_flag=True, default=False)
@click.option('--shiv', is_flag=True, default=False)
@pass_vulcan
def build_out(config: Vulcan, outdir: Path, _lock: bool, wheel: bool, sdist: bool, shiv: bool) -> None:
    "Create wheels, sdists, and shiv executables"
    # for ease of use
    if len([v for v in (shiv, wheel, sdist) if v]) != 1:
        raise click.UsageError("Must specify exactly 1 of --shiv, --wheel, or --sdist")

    should_lock = _lock and not config.no_lock

    config_settings = {}
    if not _lock:
        config_settings['no-lock'] = 'true'
    project = build.ProjectBuilder('.')
    outdir.mkdir(exist_ok=True)
    if sdist:
        dist = project.build('sdist', str(outdir), config_settings=config_settings)
    elif wheel or shiv:
        if shiv and not should_lock:
            raise click.UsageError("May not specify both --shiv and --no-lock; shiv builds must be locked")
        dist = project.build('wheel', str(outdir), config_settings=config_settings)
    else:
        assert False, 'unreachable because dist_types is required'
    if shiv:
        try:
            asyncio.get_event_loop().run_until_complete(build_shiv_apps(dist, config, outdir))
        finally:
            os.remove(dist)


async def resolve_deps_or_report(config: Vulcan, python_version: str = None) -> Tuple[List[str], Dict[str, List[str]]]:
    try:
        return await resolve_deps(flatten_reqs(config.configured_dependencies),
                                  config.configured_extras or {},
                                  python_version)

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
    if python_version is None and sys.platform != 'win32':
        try:
            # default to configured lock value, then current venv value if it exists, fallback to vulcan's
            # version
            python = get_virtualenv_python()
            python_version = subprocess.check_output(
                [str(python), '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
                encoding='utf-8').strip()

        except RuntimeError:
            pass
    install_requires, extras_require = asyncio.get_event_loop().run_until_complete(
        resolve_deps_or_report(config, python_version))
    doc = tomlkit.document()
    doc['install_requires'] = tomlkit.array(install_requires).multiline(True)  # type: ignore
    doc['extras_require'] = {
        k: tomlkit.array(v).multiline(True)  # type: ignore
        for k, v in extras_require.items()
    }
    with open(config.lockfile, 'w+') as f:
        f.write(tomlkit.dumps(doc))


@main.command()
@click.argument('req', type=Requirement.parse)
@click.option('--lock/--no-lock', '_lock', default=True)
@pass_vulcan  # order matters, closest to the function definition comes first
@click.pass_context
def add(ctx: click.Context, config: Vulcan, req: Requirement, _lock: bool) -> None:
    "Add new top-level dependency and regenerate lockfile"
    name: str = req.name  # type: ignore
    if req.extras:
        name = f'{name}[{",".join(req.extras)}]'
    try:
        venv_python = get_virtualenv_python()
    except RuntimeError:
        exit("Must be in a virtualenv to use `vulcan add`")
    subprocess.check_call([str(venv_python), '-m', 'pip', 'install', str(req)])
    if req.specifier:  # type: ignore
        # if the user gave a version spec, we blindly take that
        version = str(req.specifier)  # type: ignore
    else:
        # otherwise, we take a freeze to see what was actually installed
        freeze = subprocess.check_output([str(venv_python), '-m', 'pip', 'freeze'], encoding='utf-8').strip()
        try:
            # try and find the thing we just added
            line = next(ln for ln in freeze.split('\n') if ln.startswith(req.name))  # type: ignore
            # and parse it to a version
            spec = packaging.version.parse(str(Requirement.parse(line.strip()).specifier  # type: ignore
                                               )[2:])  # remove the == at the start
            if isinstance(spec, packaging.version.LegacyVersion):
                # this will raise a DeprecationWarning as well, so it will yell at user for us.
                version = ''
            else:
                version = f'~={spec.major}.{spec.minor}'
        except StopIteration:
            # failed to find the thing we just installed, give up.
            version = ''
    with open('pyproject.toml') as f:
        parse = tomlkit.parse(f.read())
    deps = parse['tool']['vulcan'].setdefault('dependencies', tomlkit.table())  # type: ignore
    deps[name] = version
    with open('pyproject.toml', 'w+') as f:
        f.write(tomlkit.dumps(parse))
    if not config.no_lock and _lock:
        ctx.obj = Vulcan.from_source(Path().absolute(), fail_on_missing_lock=False)
        ctx.invoke(lock)


def install_dev_dependencies(target: str = None) -> None:
    config = Vulcan.from_source(Path().absolute(), fail_on_missing_lock=False)

    try:
        virtual_env = get_virtualenv_python()
    except RuntimeError:
        exit('may not use vulcan develop outside of a virtualenv')
    pip_version = get_pip_version(virtual_env)
    if pip_version is None or pip_version < (21, 3):
        print(f"pip version {pip_version} does not support editable installs for PEP517 projects,"
              " Please upgrade your pip")

    if target is not None and target not in config.dev_dependencies:
        raise click.UsageError(f"No such dev dependency {target}")
    if config.dev_dependencies:
        for name, section in config.dev_dependencies.items():
            if target is None or name == target:
                print(f"Installing dev dependencies for {name}", flush=True)
                # print(subprocess.check_output(...)) instead of just subprocess.check_call(...)
                # purely because the CliRunner fixture isn't very good at actually capturing stdout, and it
                # breaks pytest's capsys which _is_ usually good at that
                # ah well
                print(subprocess.check_output(
                    [str(virtual_env), '-m', 'pip', 'install', *(flatten_reqs(section) or [])],
                    encoding='utf-8'),
                      flush=True)


@main.command()
@click.argument('dev_deps_target', required=False, type=str)
def develop(dev_deps_target: Optional[str]) -> None:
    install_develop()
    install_dev_dependencies(target=dev_deps_target)


if __name__ == '__main__':
    main()
