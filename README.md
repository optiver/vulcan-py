# About

This is a buildtool intended to take advantage of poetry's lockfile capabilities without having to force users
to deal with a bunch of setup in bamboo and their own projects. The intended workflow is that users will use
poetry in their dev environments to generate lockfiles, then this tool will use that lockfile to transparently
set patch-version pinned requirements to avoid incidents like EE-2936 by forcing all dependency upgrades to be
explicit.

# Quickstart

## To create a shiv app that has been configured in pyproject.toml:
1. `pip install vulcan`
2. `vulcan build --shiv -o dist`


That's it. Pip and this project will deal with:

1. Installing poetry/setuptools/toml/etc in a temporary venv
2. Generating the requirements from the lockfile
3. Transforming the metadata from poetry spec to setuptools spec
4. Creating the wheel/sdist


## To convert a project currently using setup.py or setup.cfg:

1. Convert the values in the setup.py to pyproject.toml (all keys can be copy/pasted to the toml syntax with
   the exception of dependencies and long\_description). long\_description has been replaced with the `readme` 
   key, which points to your readme file. Dependencies have their own section `[tool.vulcan.dependencies]` and
   are only used to create the lockfile.

2. Add the following block to the pyproject.toml

```ini
[build-system]
requires=['setuptools', 'vulcan']
build-backend="vulcan.build_backend"
```

3. Run `vulcan lock` and commit `vulcan.lock` if you have not already.

4. That should be it. The created files and packages should be entirely compatabile (indistinguishable except
   for the install requirements) with setup.py packages.
