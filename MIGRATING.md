# Migration

This document will detail migrating to vulcan from various other applications.

Table of Contents:

- [setuptools (setup.py)](#Setuptools)
- [Poetry](#Poetry)

## If you're not interested in the details: 

In the root directory of the project to be converted, run: 

```bash
$ pipx install vulcan[convert,cli]
$ source ./venv/bin/activate # or however you prefer to enter a virtualenv
$ pip install -U pip wheel setuptools
$ convert_pep621
```


## Setuptools

Based on [setup.cfg metadata](https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html#metadata).

Also note that "Not supported" does not mean that support would be difficult/impossible to add (many of them
would be trivial, e.x. project_urls, licence_file and licence_files, but haven't been needed yet). Please
contact one of the maintainers of vulcan if you would like one of these fields added.

If you are migrating from setuptools, you will have your config in either a setup.py or a setup.cfg. These
values will need to be moved to a pyproject.toml.  You can find a minimal starting configuration in the
[readme.md](./readme.md), then transfer the values from the old file to the pyproject.toml as described here.

### version

Can be copied over, or may be dropped entirely. If this tag is present vulcan will use it, otherwise the
version will be taken from a VERSION file if present. 

### project_urls

Becomes `urls`

### license_file, license_files

Not supported.

### long_description

Replaced by readme tag. The file specified by this tag will be read, and the contents used as the
long_description.

### long_description_content_type

Not supported.

### provides, requires, obsoletes

Not supported.

### zip_safe

Not supported.

### setup_requires

Not supported (deprecated by the concept of PEP517 build-backends in general).

### install_requires, extras_require

See Poetry -> vulcan section above for how to specify dependencies and extras in vulcan .

### use_2to3, use_2to3_fixers, use_2to3_exclude_fixters, convert_2to3_doctests

Not supported.

### scripts

Not supported.

### eager_resources, dependency_links, tests_require, namespace_packages, py_modules, data_files

Not supported.

### include_package_data

Not supported, always True. Use the MANIFEST.in to control what data files are included in the final built
wheel/shiv/sdist.

### package_data, exclude_package_data

Not supported, use MANIFEST.in.


## Poetry

Same deal here, any tags not explicitly mentioned can be copied 1-to-1. 

Migrating from poetry is the most complicated migration. This is because vulcan's metadata tags are based on
setuptools, while poetry chose to invent a separate standard. 

Metadata tags not explicitly mentioned below can be copied directly from `[tool.poetry]` to `[tool.vulcan]`

If you are using poetry, you are already using pyproject.toml so there is no need to change files.

### version

Can be copied over, or may be dropped entirely. If this tag is present vulcan will use it, otherwise the
version will be taken from a VERSION file if present. 

### authors

In poetry this is a list of strings of the form `name <email>`, e.g. `joelchristiansen <joelchristiansen@optiver.com>`

In PEP621, this is a list of tables, which have 2 keys: `name` and `email`
string if present. So:

```toml
[tool.poetry]
authors = ["joelchristiansen <joelchristiansen@optiver.com>"]
```

becomes

```toml
[project]
authors = [{name="joelchristiansen", email="joelchristiansen@optiver.com"}]
```

### maintainers

Exactly the same as authors, `maintainers` goes to `maintainer` and `maintainer_email`

### homepage, repository, documentation

Change to `urls`. No other changes. `urls` accepts a table, with the key being what the url is for and the
value being the url

### packages

Now just a list of include-strings. 

```toml
[tool.poetry]
packages = [
   { include = "vulcan", from="lib" }
]
```

becomes

```toml
[tool.vulcan]
packages = ["vulcan"]
package_dir = {"" = "lib"}
```

### include and exclude

Not supported. Please use MANIFEST.in to specify data files.

### dependencies

Poetry has invented its own version specification format, see: https://python-poetry.org/docs/versions/ for
conversion. Other than that conversion, `[tool.poetry.dependencies]` can be copied to `[tool.vulcan.dependencies]`

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
requests2 = {version="^2.13.0", extras=["security"])
```

becomes 

```toml
[tool.vulcan.dependencies]
requests = "~=2.13"
requests2 = {version="~=2.13", extras=["security"]}
```

### scripts, plugins

The semantics for PEP621 and poetry entry points are identical, the only change is the name of the table.

```toml
[tools.poetry.scripts]
vulcan = "vulcan.cli:main"

[tools.poetry.plugins.some_other_ep]
something = "vulcan.something:thing"
```

becomes

```toml
[project.scripts]
vulcan = "vulcan.cli:main"

[project.entry-points.some_other_ep]
something = "vulcan.something:thing"
```

### extras

For this, I can only explain by showing (using poetry's example and how it looks in vulcan):

```toml
[tool.poetry]
name = "awesome"

[tool.poetry.dependencies]
mandatory = "^1.0"
psycopg2 = { version = "^2.7", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
```

becomes

```toml
[package]
name = "awesome"

[tool.vulcan.depedencies]
mandatory = "~=1.0"

[tool.vulcan.extras]
mysql = ["mysqlclient~=1.3"]
pgsql = ["psycopg2~=2.7"]
```

# Working pyproject.toml

```toml
[project]
name = "package_name"
description = "Short description"  # OPTIONAL
authors = [{name="Firstname Lastname", email="firstnamelastname@optiver.com"}]  # OPTIONAL
urls = {stash="stash_url"}  # OPTIONAL
readme = "README.md"  # OPTIONAL
keywords = [ "vulcan", ]   # OPTIONAL
# see https://pypi.org/classifiers/ for allowed classifiers
classifiers = [  # OPTIONAL
    "Programming Language :: Python :: 3.9"
]
requires-python = ">=3.9"  # OPTIONAL


[project.scripts]  # OPTIONAL
entry_point="package_name.cli:main"
entry_point_two="package_name.cli:main2"

[project.entry-points.some_ep]  # OPTIONAL
another_entry_point="package_name.something:another"

[tool.vulcan.dependencies]  # OPTIONAL
common_py='*'
dataclasses='*'
requests='*'

[tool.vulcan.extras]  # OPTIONAL
some_extra=["psycopg2"]

[[tool.vulcan.shiv]]
bin_name="my_app"
console_script="entry_point"
interpreter='/usr/bin/env python3.'
extra_args="--compile-pyc"

[[tool.vulcan.shiv]]
bin_name="my_app_two"
entry_point="package_name.cli:main2"
interpreter='/usr/bin/env python3.9'
extra_args="--compile-pyc"

[tool.vulcan]
packages = [ "package_name" ]

[build-system]
# in other build systems, this would says "requires=['setuptools', 'vulcan']" and that is all that is needed
# to correctly install and use this tool
requires=['vulcan~=1.7']
build-backend="vulcan.build_backend"
```
