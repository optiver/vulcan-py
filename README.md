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
