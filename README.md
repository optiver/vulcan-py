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

`build` also supports outputing wheel and sdists, which can be used to distribute your application as a pip
package as well as a shiv binary if desired.
