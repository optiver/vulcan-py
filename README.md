# About

This is a build tool intended to make lockfiles without having to force users to deal with a bunch of setup 
in bamboo and their own projects. The intended workflow is that users will use create a lockfile with 
`vulcan lock`, then this tool will use that lockfile to transparently set patch-version pinned requirements 
to avoid incidents like EE-2936 by forcing all dependency upgrades to be explicit.

## Note:
It is possible that the config elements may change to be in compliance with
https://www.python.org/dev/peps/pep-0621

## Warn:

This project is NOT an example project, do not blindly copy/paste from any files in this project except the
README.md. This project builds itself and therefor requires some special configurations.

# Getting started

## Pre-existing vulcan project

```bash
$ mkvirtualenv -p /usr/bin/python3.6 project_name  # 1. create a virtualenv
$ pip install -U pip                               # 2. upgrade pip
$ pip install -U vulcan[cli]                       # 3. install vulcan with cli extra
$ vulcan develop                                   # 4. make an editable installation of your project
$ vulcan build -o dist/                            # 5. create a distirbution
```

## Brand new project

Steps 1-3 from above, then:

Create your project as normal, ensuring that MANIFEST.in contains the files you want


## Minimal starting configuration (pyproject.toml)

```toml
[tool.vulcan]
name = "package_name"

# This section is mandatory and may be blindly copy/pasted
[build-system]
requires = ['setuptools', 'vulcan']
build-backend = "vulcan.build_backend"
```

## Dependencies 

```toml
[tool.vulcan.dependencies]
toml='~=0.10'
setuptools='~=53.0.0'
wheel='~=0.36.2'
dataclasses='~=0.8'
```

Specify dependencies using the form: `package_name='{pep-508-spec}'`. Extras are supported in the package name.

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
shiv -p '/usr/bin/env python3.6' -e your_application.__main__:run  -o {distdir}/binary_name" --compile-pyc .
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
extra_args="--compile-pyc"
```

This section may be repeated, in which case `build` will create all the specified binaries.

`build` also supports outputting wheel and sdists, which can be used to distribute your application as a pip
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

`develop` is a convenience tool intended to replicate the effects of `pip install -e .` when developing an
application, as that command was [removed in pep 517](https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-sdist).

If you did not previously use `pip install -e .`, this command may be safely ignored. If you did, follow these
steps (assuming you have already created the lockfile) to update your development environment to use `develop`:

```
$ pip uninstall your_package_name
$ vulcan develop
```
