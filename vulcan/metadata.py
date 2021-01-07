import configparser
import os
import sys
from typing import Any, Mapping
import re


def build_metadata(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    # all keywords for SETUPTOOLS: https://setuptools.readthedocs.io/en/latest/references/keywords.html
    # all keywords for POETRY: https://python-poetry.org/docs/pyproject/
    # known CORRECT tags:
    #  - name
    #  - version
    #  - description
    #  - classifiers
    #  - keywords
    # known HANDLED tags:
    #  - (poetry -> setuptools)
    #  - homepage -> url
    #  - authors -> author
    #  - readme -> long_description
    # known UNHANDLED tags (either handled elsewhere like packages, or incompatible)
    #  - packages (handled in vulcan.options.build_packages)
    #  - entry_points (handled in vulcan.options.build_entry_points)
    #  - python_requires (handled in vulcan.options.build_packages)
    #  - include_package_data (expliclitly ignored and always set to true)
    #  - exclude_package_data (handled in MANIFEST.in)
    #  - any tags mentioned in the above links, but not mentioned here.
    config['metadata'] = {convert_tag(k): v for k, v in pyproject['tool']['poetry'].items()}
    poetry = pyproject['tool']['poetry']
    # poetry believes a package may have multiple authors, setuptools and wheel metadata disagree
    if poetry.get('authors'):
        author_re = re.compile('(?P<name>.*)(?: <(?P<email>.*)>)')
        match = author_re.match(poetry['authors'][0])
        if match:
            author, author_email = match.group('name'), match.group('email')
            config['metadata']['author'] = author
            config['metadata']['author_email'] = author_email
        else:
            config['metadata']['author'] = poetry['authors'][0]
    # poetry believes just saying "check here" is sufficient, wheels want the content and don't care where you
    # put it
    if poetry.get('readme'):
        if os.path.exists(poetry['readme']):
            with open(poetry['readme']) as f:
                config['metadata']['long_description'] = f.read()
        else:
            # I don't think this should be a failure condition.
            # This output will only be seen if pip is run with -v
            print(f"Readme configured in pyproject.toml but not found in {os.getcwd()}", file=sys.stderr)
    if poetry.get('keywords'):
        # Why these are space separated and classifiers are newline is beyond me.
        config['metadata']['keywords'] = ' '.join(poetry.get('keywords'))
    if poetry.get('classifiers'):
        config['metadata']['classifiers'] = '\n'.join(poetry.get('classifiers'))


def convert_tag(tag: str) -> str:
    return {
        'homepage': 'url'
    }.get(tag, tag)
