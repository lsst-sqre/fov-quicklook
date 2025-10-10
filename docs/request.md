次の要件のもとにFITSローダーを自作してください。

* [ ] 機能要件
  * C言語拡張で作成し高速で動作すること。
  * cfitsioを使わずに実装する
  * `src/quicklook/generator/preprocess_ccd/__init__.py`の２箇所で使われている`pyfits.open(path, memmap=False)`の置き換えとして使えれば十分
  * `RICE_1`, `GZIP_2`形式の圧縮に対応
    * https://heasarc.gsfc.nasa.gov/docs/software/fitsio/compression.html を参照
  * その他、必要に応じて情報はWeb検索をして調べること
  * `lib/fits-loader`に作成
    * `./.venv/bin/pip install ./lib/fits-loader`で使用可能にすること
  * 動作確認
      * 以下の4つのFITSバイト列で動作確認をする
      * `src/quicklook/generator/preprocess_ccd/test_preprocess_ccd.py`の`test_preprocess_ccd_raw`, `test_preprocess_ccd_calexp`の`fits_bytes`で得られるデータ
      * `../sample-data/preliminary_visit_image_2025092100190-R13_S12.fits`, `../sample-data/raw_2025092100465-R12_S21.fits`の2つのFITSファイルの内容
  * スレッド安全性
    * スレッド間でLoaderインスタンスを共有しなければ安全に使えること
  * GILを解放すること
  * Pythonでfacadeを作り、astropy.io.fitsと似たインターフェースを提供すること
    * C言語の部分は最小限にとどめること
  * インターフェース
    * FITSファイルのバイト列を入力としロード後のHDUのリストを返す
  * デコードを指定した並列度のスレッドで並行に行う
    * もし1つのHDU内でのデコードを並列に行うのが難しい場合はFITSファイルに含まれるHDUを
  * 遅延評価
    * HDU(`hdlu[3]`)やデータ領域(`hdul[2].data`)はアクセスされて初めてアクセス可能にする
  * 性能戦略
    * Loaderインスタンスの初期化は時間がかかっても良い
    * その代わりLoaderインスタンスを使い回せば性能がでるようにする
* [ ] テストコードを作ること
  * カバレッジは例外を送出するだけのブランチ以外で100%を目指す
* [ ] ドキュメント
  * 最低限の整備する
* [ ] ベンチマーク
  * 圧縮形式ごとに`astropy.io.fits`との比較を作成しドキュメントにまとめる
