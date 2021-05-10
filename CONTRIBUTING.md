# Contributing to Vulcan

## How to make a release

Note that steps 1 and 2 can be done at any point, including before actually doing your change. This might even
be preferable because it provides a nice tracking mechanism. That's not mandatory however.

### 1. Create the jira release
Go to [the jira project page](https://jira.ams.optiver.com/projects/VULCAN?selectedItem=com.atlassian.jira.jira-projects-plugin:release-page)
and create an entry of the form `vulcan-{major}.{minor}.{patch}` (e.x. vulcan-1.7.2) with
[semver](https://semver.org/) semeantics. If you're unsure about what the next version, please read the semver
page, but in short:

* If a release will break backwards compatabiliy in the CLI (either in the config or in the usage), that
  release MUST be a major version.
* If a release adds a new feature without breaking backwards compatability, that release should be a minor
  version.
* If a release fixes a bug without breaking backwards compatability or adding any new features, that release
  should be a patch version.

#### Note
As vulcan is not intended to be used as a library, there are not any guarentees on internal code compatability
and that may (though probably will not) change dramatically at any time, and the CLI/config format are the
only things guarenteed by the versioning. 

That said, it is still polite to treat the internal semantics in the same way as the CLI. 

### 2. Link any associated issues 
Go to [issues](https://jira.ams.optiver.com/projects/VULCAN/issues) and set Fix Version to the version created
above.


### 3. Release
Once all issues are closed and the release is ready:

1. click `[Release]` in the upper right corner
2. Set `Release` to `with new build`
3. Set `Plan` to `Vulcan`
4. Click `Promote`
5. Click `Release`

## Setting up dev environment
## Running pytest/flake8/mypy

## What is a wheel
