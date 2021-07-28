![Vulcan](https://raw.githubusercontent.com/optiver/vulcan-py/master/images/Vulcan_Logo.png)

---

[//]: # ( TODO: build status indicator here )

Vulcan is a build tool intended to make lockfiles without having to force users to deal with a bunch of setup 
in ci systems and their own projects. The intended workflow is that users will use create a lockfile with 
`vulcan lock`, then vulcan will use that lockfile to transparently set patch-version pinned requirements 
to avoid incidents related to transitive dependencies being implicitly upgraded.

## Warn:

Vulcan is NOT an example project, do not blindly copy/paste from any files in this project except the
README.md. This project builds itself and therefore requires some special configurations.

# Getting started

---

For instructions on how to migrate existing projects to vulcan, see [MIGRATING.md](./MIGRATING.md)

## Install vulcan (recommended)

The recommended installation method is pipx, to avoid the dependencies in vulcan conflicting with the 
dependencies in your application:

```bash
$ pip install pipx-in-pipx  # if you don't already have pipx installed
$ pipx install vulcan-py[cli,convert]
```

## Minimal starting configuration (pyproject.toml)

```toml
[package]
name = "package_name"

# This section is mandatory and may be blindly copy/pasted
[build-system]
requires = ['vulcan-py']
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

## Build the package


Assuming the above has worked, you should now be able to do the following:

```bash
$ vulcan build --wheel
```

And find a wheel in `dist/package_name-0.0.0-py3-none-any.whl`

# Command Overview

---

## build

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

## lock

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

## add

`add` is a convenience tool that will grab the most recent version of a library, add it to the pyproject.toml,
and regenerate the lockfile (if applicable)

```
$ vulcan add --help         
usage: vulcan add [-h] [--no-lock] reqspec                               
                                                                         
positional arguments:                                                    
  reqspec                                                                
                                                                         
optional arguments:                                                      
  -h, --help  show this help message and exit                            
  --no-lock                                                              
```


## develop

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

# Plugins

Vulcan supports a minimal plugin mechanism, which can be used to trigger arbitrary build steps during the
build process.

## vulcan.pre_build

Pre-build steps take place immediately before creating the wheel or sdist output. As an example, you could
have a plugin that populates a target file with the build time:

```python
# myplugin.py
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime
def populate_buildtime(config: Optional[Dict[str, str]]) -> None:
   assert config is not None
   assert 'target' in config
   Path(config['target']).write_text(f'{datetime.now():%Y-%m-%d %H:%M}')
```

```toml
# in the plugin's pyproject.toml
[project.entry-points."vulcan.pre_build"]
myplugin="myplugin:populate_datetime"
```

```toml
# in the project's pyproject.toml
[tool.vulcan]
plugins = ["myplugin"]
packages = ["myproject"]

[tool.vulcan.plugin.myplugin]
target = "myproject/__BUILD_TIME__"
```

# Tips

---

## Pinning vulcan deps
As vulcan itself is not pinned, it is theoretically possible for an upstream dependency of vulcan to introduce
a bug. If you would like to eliminate this possibility, you can add an extra to your application that pins
vulcan, which will lock in the dependencies of vulcan itself. Something along the lines of:

```toml
[tool.vulcan.extras]
build = ["vulcan~=1.2"]
```

And then install your tox build job with a configuration that includes the line:

```ini
[toxenv:build]
extras = 
    build
```

And this will ensure that vulcan and all its dependencies are pinned in your lockfile and used while building.

# License

---

vulcan is:

Copyright 2021 Optiver

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

```
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See
the License for the specific language governing permissions and limitations under the License.

## tox and vulcan

To make sure that tox and vulcan can interact comfortably, be sure to add your `vulcan.lock` to your `MANIFEST.in`. 
This will ensure that while building your package, tox also picks up the locked dependencies.
