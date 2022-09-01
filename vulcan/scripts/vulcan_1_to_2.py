from pathlib import Path
import sys

import tomlkit


def convert() -> None:
    with open('./pyproject.toml') as f:
        pyproject = tomlkit.loads(f.read())
        project = pyproject.get('project')
        if not project:
            exit("Refusing to try and migrate a pyproject.toml without any [project] section")
        tool = pyproject.setdefault('tool', tomlkit.table(is_super_table=True))
        setuptools = tool.setdefault('setuptools', tomlkit.table(is_super_table=True))
        vulcan = tool.get('vulcan', {})
        setuptools_dynamic = setuptools.setdefault('dynamic', tomlkit.table(is_super_table=True))
    dynamic = project.get('dynamic', [])

    # fix dynamic
    for vulcan_key, real_key in (('dependencies', 'dependencies'),
                                 ('version', 'version'), ('extras', 'optional-dependencies')):
        if vulcan_key in vulcan and ('dynamic' not in project or real_key not in project['dynamic']):
            dynamic.append(real_key)

    # fix version discovery
    version_file = next(Path().rglob('VERSION'), None)
    if 'version' not in project and version_file is not None:
        dynamic.append('version')
        if 'version' in setuptools_dynamic:
            print("version already configured in [tool.setuptools.dynamic], not changing", file=sys.stderr)
        else:
            version_table = tomlkit.table(is_super_table=True)
            setuptools_dynamic['version'] = version_table
            version_table['file'] = str(version_file)
        if 'version' in vulcan:
            del vulcan['version']

    # fix packages
    if 'packages' in vulcan:
        setuptools_packages = setuptools.setdefault('packages', tomlkit.table(is_super_table=True))
        find = setuptools_packages.setdefault('find', tomlkit.table(is_super_table=True))
        include = find.setdefault('include', tomlkit.array())
        include.extend(vulcan['packages'])
        del vulcan['packages']

    build_system = tomlkit.table()
    pyproject['build-system'] = build_system
    build_system['requires'] = ['vulcan-py~=2.0']
    build_system['build-backend'] = 'vulcan.build_backend'

    if dynamic:
        project['dynamic'] = dynamic

    with open('./pyproject.toml', 'w+') as f:
        f.write(tomlkit.dumps(pyproject))
