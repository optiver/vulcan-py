# About

This is a buildtool intended to take advantage of poetry's lockfile capabilities without having to force users
to deal with a bunch of setup in bamboo and their own projects. The intended workflow is that users will use
poetry in their dev environments to generate lockfiles, then this tool will use that lockfile to transparently
set patch-version pinned requirements to avoid incidents like EE-2936 by forcing all dependency upgrades to be
explicit.

# Quickstart

1. `git clone ssh://git@stash.ams.optiver.com:7999/~joelchristiansen/vulcan.git`
2. Ensure pip >=19.0
3. `pip install .`  
Or, to create the wheel without actually installing:
3. `pip wheel .  -w build/ --no-deps`


That's it. Pip and this project will deal with:

1. Installing poetry/setuptools/toml/etc in a temporary venv
2. Generating the requirements from the lockfile
3. Transforming the metadata from poetry spec to setuptools spec
4. Creating the wheel/sdist


If you are using shiv to create the application, you can then directly use the generated wheel to create an
application, e.g. `shiv -p '/usr/bin/env python3.6' -c your_entry_point  -o {distdir}/your_bin_name -E --compile-pyc appname-1.2.3-py3-none-any.whl`


## To convert a project currently using setup.py or setup.cfg:

1. Convert the values in the setup.py to pyproject.toml (such that poetry is happy to run `poetry lock` without
complaint, see [here](https://python-poetry.org/docs/pyproject/) for more specific instructions).

2. Add the following block to the pyproject.toml

```ini
[build-system]
requires=['setuptools', 'vulcan']
build-backend="vulcan.build_backend"
```

3. Run `poetry lock` and commit `poetry.lock` if you have not already.

4. That should be it. The created files and packages should be entirely compatabile (indistinguishable except
   for the install requirements) with setup.py packages.
