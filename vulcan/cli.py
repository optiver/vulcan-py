import argparse
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union

import build
import build.env
import toml
from vulcan import Vulcan
from vulcan.build_backend import install_develop
from vulcan.builder import resolve_deps


class PrettyTomlEncoder(toml.TomlEncoder):  # type: ignore
    def dump_list(self, v: List[Any]) -> str:
        retval = "["
        for u in v:
            retval += "\n   " + str(self.dump_value(u)) + ","
        retval += "]"
        return retval


def to_pep508(lib: str, req: Union[str, Dict[str, str]]) -> str:
    if isinstance(req, str):
        # e.g. "options_sdk", "~=1.2.3" -> "options_sdk~=1.2.3"
        return f'{lib}{req}'
    extras = f'[{",".join(req["extras"])}]' if 'extras' in req else ''
    # "options_sdk", {"version": "~=1.2.3", "extras="networkx,git"} -> "options_sdk[networkx,git]~=1.2.3"
    return f'{lib}{extras}{req["version"]}'


def build_shiv_apps(from_dist: str, vulcan: Vulcan, outdir: Path) -> List[Path]:
    results = []
    for app in vulcan.shiv_options:
        try:
            if not app.with_extras:
                dist = from_dist
            else:
                dist = f'{from_dist}[{",".join(app.with_extras)}]'
            cmd = ['shiv', dist, '-o', str(outdir / app.bin_name)]
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

    lock = subparsers.add_parser('lock')
    lock.set_defaults(subcommand='lock')

    develop = subparsers.add_parser('develop')
    develop.set_defaults(subcommand='develop')
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
            try:
                build_shiv_apps(dist, config, args.outdir)
            finally:
                os.remove(dist)
    elif args.subcommand == 'lock':
        install_requires, extras_require = resolve_deps(
            [to_pep508(k, v) for k, v in config.configured_dependencies.items()],
            config.configured_extras or {})
        with open(config.lockfile, 'w+') as f:
            #  toml type annotations claim there is no "encoder" argument.
            #  toml type annotations lie
            toml.dump({'install_requires': install_requires,  # type: ignore
                       'extras_require': extras_require},
                      f, encoder=PrettyTomlEncoder())
    elif args.subcommand == 'develop':
        # do note that when using this command specifically in this project, you MUST call it as
        # `python vulcan/cli.py develop` the first time.
        # All other projects, you can just do `vulcan devleop` and that's fine.
        install_develop()
    else:
        raise ValueError('unknown subcommand {args.subcommand!r}')


if __name__ == '__main__':
    main()
