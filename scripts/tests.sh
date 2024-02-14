#! /bin/bash

python3.11 -m venv .build-venv
source .build-venv/bin/activate
pip install -e .[cli]
pip install pytest pytest-asyncio pkginfo