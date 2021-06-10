import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, TypeVar, Union

import build
import build.env
import packaging.version
import tomlkit
from pkg_resources import Requirement

from vulcan import Vulcan, flatten_reqs
from vulcan.build_backend import get_virtualenv_python, install_develop
from vulcan.builder import resolve_deps

T = TypeVar('T')


def build_shiv_apps(from_dist: str, vulcan: Vulcan, outdir: Path) -> List[Path]:
    results = []
    for app in vulcan.shiv_options:
        try:
            if not app.with_extras:
                dist = from_dist
            else:
                dist = f'{from_dist}[{",".join(app.with_extras)}]'
            cmd = [sys.executable, '-m', 'shiv', dist, '-o', str(outdir / app.bin_name)]
            if app.console_script:
                cmd += ['-c', app.console_script]
            if app.entry_point:
                cmd += ['-e', app.entry_point]
            if app.interpreter:
                cmd += ['-p', app.interpreter]
            if app.extra_args:
                cmd += shlex.split(app.extra_args)
            res = subprocess.run(cmd)
            if res.returncode != 0:
                raise SystemExit(res.returncode)
            results.append(outdir / app.bin_name)
        except KeyError as e:
            raise KeyError('missing config value in pyproject.toml: {e}') from e
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()
    build = subparsers.add_parser('build')
    build.set_defaults(subcommand='build')
    dist_types = build.add_mutually_exclusive_group()
    dist_types.add_argument('--sdist', action='store_true')
    dist_types.add_argument('--wheel', action='store_true')
    dist_types.add_argument('--shiv', action='store_true')
    build.add_argument('-o', '--outdir', default='dist/', type=Path)
    build.add_argument('--no-lock', action='store_true')

    lock = subparsers.add_parser('lock')
    lock.set_defaults(subcommand='lock')

    develop = subparsers.add_parser('develop')
    develop.set_defaults(subcommand='develop')

    add = subparsers.add_parser('add')
    add.set_defaults(subcommand='add')
    add.add_argument('reqspec')
    add.add_argument('--noinstall', action='store_true')
    return parser


def build_out(config: Vulcan, args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    project = build.ProjectBuilder('.')
    if not args.outdir.exists():
        args.outdir.mkdir()
    config_settings = {}
    if args.no_lock:
        config_settings['no-lock'] = 'true'
    if args.sdist:
        dist = project.build('sdist', str(args.outdir), config_settings=config_settings)
    elif args.wheel or args.shiv:
        if args.shiv and (args.no_lock or config.no_lock):
            parser.error("May not specify both --shiv and --no-lock; shiv builds must be locked")
        dist = project.build('wheel', str(args.outdir), config_settings=config_settings)
    else:
        parser.error("Must supply one of --sdist, --wheel, or --shiv")
    if args.shiv:
        try:
            build_shiv_apps(dist, config, args.outdir)
        finally:
            os.remove(dist)


def _intersperse_nl(vals: Iterable[T]) -> Iterable[Union[T, tomlkit.items.Whitespace]]:
    for item in vals:
        yield item
        yield tomlkit.nl()


def lock(config: Vulcan, args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    install_requires, extras_require = resolve_deps(flatten_reqs(config.configured_dependencies),
                                                    config.configured_extras or {})
    doc = tomlkit.document()
    doc['install_requires'] = tomlkit.array(install_requires).multiline(True)  # type: ignore
    doc['extras_require'] = {k: tomlkit.array(v).multiline(True)   # type: ignore
                             for k, v in extras_require.items()}
    with open(config.lockfile, 'w+') as f:
        f.write(tomlkit.dumps(doc))


def add(req: Requirement) -> None:
    name: str = req.name  # type: ignore
    if req.extras:
        name = f'{name}[{",".join(req.extras)}]'
    try:
        venv_python = get_virtualenv_python()
    except RuntimeError:
        exit("Must be in a virtualenv to use `vulcan add`")
    subprocess.check_call([venv_python, '-m', 'pip', 'install', str(req)])
    if req.specifier:  # type: ignore
        version = str(req.specifier)  # type: ignore
    else:
        freeze = subprocess.check_output([venv_python, '-m', 'pip', 'freeze'], encoding='utf-8').strip()
        line = next(ln for ln in freeze.split('\n') if ln.startswith(req.name))  # type: ignore
        try:
            spec = packaging.version.parse(str(Requirement.parse(line.strip()).specifier  # type: ignore
                                               )[2:])  # remove the == at the start
            if isinstance(spec, packaging.version.LegacyVersion):
                version = ''
            else:
                version = f'~={spec.major}.{spec.minor}'
        except StopIteration:
            version = ''
    with open('pyproject.toml') as f:
        parse = tomlkit.parse(f.read())
    deps = parse['tool']['vulcan'].setdefault('dependencies', tomlkit.table())  # type: ignore
    deps[name] = version  # type: ignore
    with open('pyproject.toml', 'w+') as f:
        f.write(tomlkit.dumps(parse))


def main(argv: List[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = Vulcan.from_source(Path().absolute())
    if args.subcommand == 'add':
        req = Requirement.parse(args.reqspec)
        add(req)
        if not args.noinstall and os.environ.get('VIRTUAL_ENV') is not None:
            install_develop()
    elif args.subcommand == 'build':
        build_out(config, args, parser)
    elif args.subcommand == 'lock':
        lock(config, args, parser)
    elif args.subcommand == 'develop':
        # do note that when using this command specifically in this project, you MUST call it as
        # `python vulcan/cli.py develop` the first time.
        # All other projects, you can just do `vulcan devleop` and that's fine.
        return install_develop()
    else:
        raise ValueError('unknown subcommand {args.subcommand!r}')


if __name__ == '__main__':
    main()
