# Contributing

Use Python 3.10+ and install `python -m pip install -e ".[dev]"`.

Run pytest, Ruff lint/format checks, `python -m build` and the offline demo before
submitting a change. Tests must use mocked HTTP and must not start paid jobs.

Useful contributions include recovery cases, large-file handling, output formats and
clear examples. Include the command, Python/OS version and a redacted error in issues.
Never include API keys, storage credentials, signed URLs or private collection data.
