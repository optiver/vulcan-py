# Contributing to Vulcan

## How to make a release

Note that steps 1 and 2 can be done at any point, including before actually doing your change. This might even
be preferable because it provides a nice tracking mechanism. That's not mandatory however.

### 1. Create the jira release
Go to [the jira project page](https://jira.ams.optiver.com/projects/VULCAN?selectedItem=com.atlassian.jira.jira-projects-plugin:release-page)
and create an entry of the form `vulcan-{major}.{minor}.{patch}` (e.x. vulcan-1.7.2) with
[semver](https://semver.org/) semantics. If you're unsure about what the next version, please read the semver
page, but in short:

* If a release will break backwards compatibility in the CLI (either in the configuration or in the usage),
  that release MUST be a major version.
* If a release adds a new feature without breaking backwards compatibility, that release should be a minor
  version.
* If a release fixes a bug without breaking backwards compatibility or adding any new features, that release
  should be a patch version.

#### Note
As vulcan is not intended to be used as a library, there are not any guarantees on internal code compatibility
which may (though probably will not) change dramatically at any time. 

The CLI/configuration format are the only things guaranteed by the versioning. 

That said, it is still polite to treat the internal semantics in the same way as the CLI. 

### 2. Link any associated issues 
Go to [issues](https://jira.ams.optiver.com/projects/VULCAN/issues) and set `Fix Version` to the version created
above.


### 3. Release
Once all issues are closed and the release is ready:

1. click `[Release]` in the upper right corner
2. Set `Release` to `with new build`
3. Set `Plan` to `Vulcan`
4. Click `Promote`
5. Click `Release`

## Setting up dev environment
Unfortunately, because pep-517 disabled editable installs, and because vulcan builds itself, it is not 
possible to correctly do "vulcan develop" for vulcan project. Therefor, you need to `pip install .` any time
you want to run test any changes. Al Note that this does not apply to tox commands, as those will always rebuild
vulcan. To set up a basic vulcan install, therefore:

```bash
$ mkvirtualenv -p /usr/bin/python3.6 vulcan
$ pip install -U pip
$ pip install .[pep621,convert,cli]
```

You can then (optionally) do something like:

```bash
$ alias vulcan='PYTHONPATH=. python vulcan/cli.py'
$ pip uninstall vulcan 
```

Which will be an imperfect emulation of an editable install.

## Running pytest/flake8/mypy
The goal for testing here is that every test command should be easy to run fully (no extra required arguments,
everything in config, no special rules). 

So, to run pytest:

```bash
$ pytest
```

And to run flake8:

```bash
$ flake8
```

And to run mypy:

```bash
$ mypy
```

In general, this should be true of ANY new tool as well.

## What is a wheel

Wheels are defined in [PEP-0427](https://www.python.org/dev/peps/pep-0427/). For a full specification please
read that.

The structure of wheel with packages `my_package_one` and `my_package_too` with name `my_project` and version
`1.2.3` will look like the following:

```
     A    |  B  | C | D  | E | F 
my_package-1.2.3-py3-none-any.whl
```

* A: package name
* B: version
* C: target python version
* D: abi tag
* E: platform
* F: file extensioversion
* D: abi tag
* E: platform
* F: file extension
