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
requires=['setuptools', 'vulcan']
build-backend="vulcan.build_backend"
```

