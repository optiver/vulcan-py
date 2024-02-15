## How to run the tests

```bash
python3.11 -m venv .venv 
source .venv/bin/activate
pip install -e .[cli] pytest pytest-asyncio pkginfo
pytest tests
```

## Testing issues?

It could be that your lock file is not resolving to the same thing.