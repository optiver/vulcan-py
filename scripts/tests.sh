#! /bin/bash

python3.11 -m venv .build-venv
source .build-venv/bin/activate
pip install -e .[cli]
pip install pytest pytest-asyncio pkginfo

#pytest tests tests/cli/test_cli.py


from __future__ import annotations