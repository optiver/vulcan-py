# Migration

This document will detail migrating to vulcan from various other applications.

Table of Contents:

- [Poetry](#Poetry)
- [setuptools (setup.py)](#setuptools)

## Poetry

Migrating from poetry is the most complicated migration. This is because vulcan's metadata tags are based on
setuptools, while poetry chose to invent a separate standard. 

Metadata tags not explicitly mentioned below can be copied directly from `[tool.poetry]` to `[tool.vulcan]`

### version

Can be copied over, or may be dropped entirely. If this tag is present vulcan will use it, otherwise the
version will be taken from a VERSION file if present. 

### authors

In poetry this is a list of strings of the form `name <email>`, e.g. `joelchristiansen <joelchristiansen@optiver.com>`

In vulcan, this is instead two tags, `author` and `author_email` which are both optional and expect a single
string if present. So:

```toml
authors = ["joelchristiansen <joelchristiansen@optiver.com>"]
```

becomes

```toml
author = "joelchristiansen"
author_email = "joelchristiansen@optiver.com"
```

### maintainers

Exactly the same as authors, `maintainers` goes to `maintainer` and `maintainer_email`

### homepage, repository, documentation

Change to `url`. No other changes. `url` currently only accepts a single string, this could be changed to
accept a list if the use case for having separate homepages and repository links is compelling.

### packages

Now just a list of include-strings. Alternative source directories are not currently supported, but could be
added if requested.

```toml
packages = [
   { include = "vulcan" }
]
```

becomes

```toml
packages = ["vulcan"]
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

### dev-dependencies

Not supported, as vulcan is not a one-stop-shop tool for all development tools. Rather vulcan is specifically
for locking and building.

### scripts, plugins

Poetry treats console\_scripts entry points specially, and gives them a specific section. Vulcan does not.

```toml
[tools.poetry.scripts]
vulcan = "vulcan.cli:main"

[tools.poetry.plugins.some_other_ep]
something = "vulcan.something:thing"
```

becomes

```toml
[tools.vulcan.entry_points.console_scripts]
vulcan = "vulcan.cli:main"

[tools.vulcan.entry_points.some_other_ep]
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
[tool.vulcan]
name = "awesome"

[tool.vulcan.depedencies]
mandatory = "~=1.0"

[tool.vulcan.extras]
mysql = ["mysqlclient~=1.3"]
pgsql = ["psycopg2~=2.7"]
```

### urls

Not supported.
