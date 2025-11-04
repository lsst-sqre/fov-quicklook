# FOV-Quicklook Backend

## Installation

```bash
~/minicona3/envs/py3_13/bin/python -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/pip install -e '.[dev]'
```

## Testing

```bash
./.venv/bin/pytest
```

## TODO

* Translate `*.ja.md` to English and create `*.md`.
  * If there is already a `*.md` corresponding to `*.ja.md`, also translate and overwrite it.
* Achieve 100% test coverage
