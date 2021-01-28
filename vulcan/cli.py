import argparse
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Union

import build
import build.env
from vulcan import Vulcan


def to_pep508(lib: str, req: Union[str, Dict[str, str]]) -> str:
    if isinstance(req, str):
        # e.g. "options_sdk", "~=1.2.3" -> "options_sdk~=1.2.3"
        return f'{lib}{req}'
    extras = f'[{req["extras"]}]' if 'extras' in req else ''
    # "options_sdk", {"version": "~=1.2.3", "extras="networkx,git"} -> "options_sdk[networkx,git]~=1.2.3"
    return f'{lib}{extras}{req["version"]}'


def build_shiv_app(from_dist: str, vulcan: Vulcan, outdir: Path) -> Path:
    try:
        cmd = ['shiv', from_dist, '-o', str(outdir / vulcan.shiv_options.bin_name)]
        if vulcan.shiv_options.console_script:
            cmd += ['-c', vulcan.shiv_options.console_script]
        if vulcan.shiv_options.entry_point:
            cmd += ['-e', vulcan.shiv_options.entry_point]
        if vulcan.shiv_options.interpreter:
            cmd += ['-p', vulcan.shiv_options.interpreter]
        if vulcan.shiv_options.extra_args:
            cmd += shlex.split(vulcan.shiv_options.extra_args)
        subprocess.run(cmd)
        return outdir / vulcan.shiv_options.bin_name
    except KeyError as e:
        raise KeyError('missing config value in pyproject.toml: {e}') from e


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

    lock = subparsers.add_parser('lock')
    lock.add_argument('--with-extras', nargs="+")
    lock.set_defaults(subcommand='lock')
    return parser


def main(argv: List[str] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = Vulcan.from_source(Path().absolute())
    if args.subcommand == 'build':
        project = build.ProjectBuilder('.')
        if not args.outdir.exists():
            args.outdir.mkdir()
        if args.sdist:
            before = set(args.outdir.iterdir())
            project.build('sdist', str(args.outdir))
            dist = next(iter(set(args.outdir.iterdir()) - before))
        if args.wheel or args.shiv:
            before = set(args.outdir.iterdir())
            project.build('wheel', str(args.outdir))
            dist = next(iter(set(args.outdir.iterdir()) - before))
        if args.shiv:
            build_shiv_app(dist, config, args.outdir)
            os.remove(dist)
    elif args.subcommand == 'lock':
        builder = build.env.IsolatedEnvBuilder()
        with builder as pipenv:
            print("Installing to a temporary isolated environment")
            pipenv.install([to_pep508(lib, req) for lib, req in config.configured_dependencies.items()])
            if args.with_extras and config.metadata.extras_require is not None:
                for extra, reqs in config.metadata.extras_require.items():
                    if extra in args.with_extras:
                        pipenv.install(reqs)
            site_pkgs = next(iter(Path(str(builder._path)).glob('lib/*/site-packages')))
            frozen = subprocess.check_output(
                [pipenv.executable, '-m', 'pip', 'list', '--format=freeze', '--path', site_pkgs],
                encoding='utf-8')
            deps = [dep for dep in frozen.split('\n') if not dep.startswith(config.metadata.name)]
        with open(config.lockfile, 'w+') as f:
            f.write('\n'.join(deps))
    else:
        raise ValueError('unknown subcommand {args.subcommand!r}')
