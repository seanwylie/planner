# Contributing

Experimental software, maintained as time permits. Large unsolicited changes are
unlikely to be merged. Forking is a legitimate outcome.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH="$(dirname "$PWD")" .venv/bin/pytest -q
```

The suite is small on purpose. Tests that call Cursor, OpenAI, or Bedrock are not
welcome unless they are fully mocked.

Do not add a `bones` submodule. Bones is optional and operator-attached.

See [SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
