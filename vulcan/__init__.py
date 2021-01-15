from pathlib import Path

with (Path(__file__).parent / 'VERSION').open() as f:
    __VERSION__ = f.read().strip()
