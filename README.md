# About

This is a buildtool intended to take advantage of poetry's lockfile capabilities without having to force users
to deal with a bunch of setup in bamboo and their own projects. The intended workflow is that users will use
poetry in their dev environments to generate lockfiles, then this tool will use that lockfile to transparently
set patch-version pinned requirements to avoid incidents like EE-2936 by forcing all dependency upgrades to be
explicit.

# Minimal starting config

```toml
[tool.vulcan]
name = "package_name"

# This section is mandatory and may be blindly copy/pasted
[build-system]
requires = ['setuptools', 'vulcan']
build-backend = "vulcan.build_backend"
```

# Command Overview

## `vulcan build`

```
$ vulcan build --help
usage: vulcan build [-h] [--sdist | --wheel | --shiv] [-o OUTDIR]

optional arguments:
  -h, --help            show this help message and exit
  --sdist
  --wheel
  --shiv
  -o OUTDIR, --outdir OUTDIR
```

Vulcan build gives a way to create wheels, sdists, and shiv applications. Instead of having the following in
tox.ini:
```
shiv -p '/usr/bin/env python3.6' -e your_application.__main__:run  -o {distdir}/binary_name" -E --compile-pyc .
```

You can instead have only 
```
vulcan build --shiv -o {distdir}
```
and have the actual  configuration for that command in your pyproject.toml:

```toml
[[tool.vulcan.shiv]]
bin_name="binary_name"
entry_point="your_application.__main__:run"
interpreter="/usr/bin/env python3.6"
extra_args="-E --compile-pyc"
```

This section may be repeated, in which case `build` will create all the specified binaries.

`build` also supports outputing wheel and sdists, which can be used to distribute your application as a pip
package as well as a shiv binary if desired.

## `vulcan lock`

```
$ vulcan lock --help

usage: vulcan lock [-h]

optional arguments:
  -h, --help  show this help message and exit
```

Vulcan lock supports no arguments (except --help) and takes no options. This command takes the dependencies
specified in `[tool.vulcan.dependencies]` and resolves them into a set of patch-version pinned dependencies,
then writes that into `vulcan.lock` (lockfile is configurable with the `lockfile` setting under `[tool.vulcan]`).

This command will update any dependencies that have had new releases (compatible with your dependencies and
all other package's requirements), and will error if it is not possible to find a resolution. This should not
be done automatically, and should always involve some extra testing when used (since the dependencies are
being updated and may introduce a bug).

## `vulcan develop`

```
$ vulcan develop --help
usage: vulcan develop [-h]

optional arguments:
  -h, --help  show this help message and exit
```

`develop` is a convienence tool intended to replicate the effects of `pip install -e .` when developing an
application, as that command was [removed in pep 517](https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-sdist).

If you did not previously use `pip install -e .`, this command may be safely ignored. If you did, follow these
steps (assuming you have already created the lockfile) to update your development environment to use `develop`:

```
$ pip uninstall your_package_name
$ vulcan develop
```
