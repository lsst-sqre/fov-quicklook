## 全体

アプリケーション全体の設計、独自の用語は`/docs/concept.ja.md`を参照。

## Pythonについて

* Python 3.13を使う
* Python環境は`./.venv`を使う
  * コマンドもその中のものを使う。`./.venv/bin/python`、`./.venv/bin/pip`、`./.venv/bin/pytest`など
* 型ヒントを積極的に使う
* テスト
  * `./.venv`の環境を使う
  * pytestを使う
  * `class Test*`ではなく`def test_*`関数でテストを書く
  * 実コードに対応するテストコードは`src/quicklook`以下のストラクチャをそのまま`tests`以下に作る。
    * 例えば`src/quicklook/module/submodule.py`に対応するテストコードは`tests/module/test_submodule.py`に置く。
    * 実コードが`src/quicklook/a/__init__.py`の場合は`tests/a/test___init__.py`に置く。
  * 
* 使用ライブラリ
  * SQLAlchemy2
    * 新しいAPIを使う。(https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html)
* コメント
  * 関数名、引数の名前から自明のコメントは不要
  * より抽象度の高い説明を書く

## markdownについて

* `*.ja.md`は日本語で書かれたドキュメントで、これを英訳するよう指示されたら対応する`*.md`を生成する。
