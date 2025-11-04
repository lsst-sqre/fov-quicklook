# FOV-Quicklook Backend

## インストール

```bash
~/minicona3/envs/py3_13/bin/python -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/pip install -e '.[dev]'
```

## テスト

```bash
./.venv/bin/pytest
```

## TODO

* `*.ja.md`を英訳して`*.md`を作る。
  * すでに`*.ja.md`に対応する`*.md`があった場合も、英訳をし上書きする。
* テストカバレッジを100%にする
