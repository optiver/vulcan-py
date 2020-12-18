import configparser
from typing import Any, Mapping


def build_metadata(config: configparser.ConfigParser, pyproject: Mapping[str, Any]) -> None:
    # naive, doesn't fully work
    # all keywords for SETUPTOOLS: https://setuptools.readthedocs.io/en/latest/references/keywords.html
    # all keywords for POETRY: https://python-poetry.org/docs/pyproject/
    # known CORRECT tags:
    #  - name
    #  - version
    #  - description
    # known UNHANDLED tags (either handled elsewhere like packages, or incompatable)
    #  - packages (handled in vulcan.build_backend.build_packages)
    #  - entry_points (handled in vulcan.build_backend.build_entry_points)
    config['metadata'] = {k: v for k, v in pyproject['tool']['poetry'].items()}
