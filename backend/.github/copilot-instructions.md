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
  * 各モジュールに対応するテストコードは同じモジュール内に`test_*.py`として配置する。
    * 例えば`src/quicklook/job/__init__.py`に対応するテストコードは`src/quicklook/job/test_job.py`に置く。
    * pytestは`tests/`ディレクトリと`src/`ディレクトリの両方からテストファイルを検出する。
  * 
* 使用ライブラリ
  * SQLAlchemy2
    * 新しいAPIを使う。(https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html)
* コメント
  * 関数名、引数の名前から自明のコメントは不要
  * より抽象度の高い説明を書く

## markdownについて

* `*.ja.md`は日本語で書かれたドキュメントで、これを英訳するよう指示されたら対応する`*.md`を生成する。
