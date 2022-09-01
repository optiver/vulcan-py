![Vulcan](https://raw.githubusercontent.com/optiver/vulcan-py/master/images/Vulcan_Logo.png)

---

Vulcan supports building python>=3.6. Vulcan itself may only be installed in python>=3.7. 
The recommended installation is via pipx. This will save a lot of pain with respect to conflicting versions,
as well as having multiple python versions in various projects.

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
[project]
name = "package_name"
dynamic = ['version']

# This section is mandatory and may be blindly copy/pasted
[build-system]
requires = ['vulcan-py']
build-backend = "vulcan.build_backend"
```

## Vulcan configuration

Vulcan uses setuptools internally, so any configuration specified in the 
[setuptools pyproject.toml config](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html) will
be respected here.

In addition, there are some vulcan-specific configurations which may be specified under `[tool.vulcan]`:

### no-lock

If set, ignore the lockfile when building wheels and installing locally. It is an error to use no-lock with a
shiv build. This may be overridden with `vulcan build --no-lock` or `vulcan build --lock`.

Generally, no-lock should be used with libraries, and should not be used with applications. This is due to the
fact that having multiple libraries with locked dependencies tends to be very difficult, with the locked
dependencies conflicting almost immediately.

```toml
[tool.vulcan]
no-lock = true
```

### lockfile

If set, allows you to specify the name of the lockfile. Defaults to `vulcan.lock`

```toml
[tool.vulcan]
lockfile = "vulcan-2.lock"
```

### python-lock-with

By default, vulcan decides which python to use to generate a lockfile based on the currently active
virtualenv. If there is not a currently active virtualenv, it will default to whichever version of python
vulcan itself was installed with. Both of these behaviors can be overridden with the `python-lock-with` key,
which specifies which python should be used to lock

```toml
[tool.vulcan]
python-lock-with = "3.9"
```

### plugins

Vulcan supports plugins, which can be called as a part of the build system to do some action on the
in-progress build. These are registered via [entry points](https://github.com/optiver/vulcan-py#plugins), and
to ensure there are not any accidental plugins activated they must be specified in the plugins config argument
as well.

```toml
[tool.vulcan]
plugins = ["plug1", "plug2"]
```

### shiv

This repeatable section allows configuration of a shiv command to be called when invoking `vulcan build --shiv`.
There are some mandatory keys, and some optional keys available.

Note the double brackets, this is what makes the section repeatable.

```toml
[[tool.vulcan.shiv]]
bin_name = "output_binary_name"    # mandatory
console_script = "console_script_name"      #| Pick exactly one of
entry_point = "path.to.entry_point:main"    #|
interpreter = "/usr/bin/env python3.9"  # optional
with_extras = ["extra1", "another_extra"]  # optional
extra_args = "--any --other --shiv --arguments"
```


### dependencies

This and the next section make the core of vulcan's functionality. These are the top-level unlocked
dependencies for your application or library. With no-lock, these are translated directly into wheel
dependencies without modification. Normally, these are used to determine the contents of the lockfile.

```toml
[tool.vulcan.dependencies]
requests=""  # no specific version
lxml="~=4.0"  # with a version specification
'build[virtualenv]' = ""   # with extras
# build = {version="", extras=["virtualenv"]}  # different way of specifying extras
```

Note that if this section is specified, it is REQUIRED to put "dependencies" into the `dynamic` key in the
`[project]` section of pyproject.toml

### extras

This section is similar to the above section, and is used to specify additional extras your application may
provide. These are also used in resolving the lockfile if no-lock is not present, and it must be possible to
install all extras at the same time.

```toml
[tool.vulcan.extras]
extra1 = ["requests[socks]~=2.0"]
extra2 = ["click"]
```

### dev-dependencies

Finally, this section is used to specify any dependencies used for development, such as mypy or pytest. These
are NOT used in resolving the lockfile, and are installed when `vulcan develop` is run (in addition to
installing the application as an editable install, equivalent to `pip install -e .`). It is possible to only
install a single set of dev dependencies with `vulcan develop {key}` (e.x `vulcan develop static-analysis`)

```toml
[tool.vulcan.dev-dependencies.test]
pytest=""
coverage=""
pytest-asyncio=""

[tool.vulcan.dev-dependencies.static-analysis]
flake8=""
mypy=""
types-dataclasses=""
```

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

Copyright 2021 Optiver IP B.V.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance
with the License. You may obtain a copy of the License at

```
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or explicitly agreed by an authorized representative of Optiver IP B.V. in
writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. Please see the License for the specific language governing
permissions and limitations under the License.


## tox and vulcan

To make sure that tox and vulcan can interact comfortably, be sure to add your `vulcan.lock` to your `MANIFEST.in`. 
This will ensure that while building your package, tox also picks up the locked dependencies.


# Migrating

Vulcan contains 2 conversion scripts: convert_pep621, and convert_vulcan2. 
The first script will convert any non-pyproject.toml project into vulcan and pyproject.toml. 
The second will convert vulcan~=1 projects into vulcan 2. 
These scripts are for convenience and provided as best-effort only, and may not perfectly convert all possible projects.
