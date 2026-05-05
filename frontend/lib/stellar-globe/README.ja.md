<!-- 
* app, stellar-globe, react-stellar-globe, react-draggable-dialogなどのコンポーネント目は `` で囲む
-->
# Stellar Globe

<!-- 以下の箇条書きを文章にする -->
* 全天のビューワー
  * Hyper Suprime-CamのPublic Data Releaseで使われている
* 任意の位置を任意の倍率で高速に表示できる
  * WebGLの利用により描画性能がよい
* 複数バンドのデータから動的にカラー画像を生成可能
* hscMap形式、HiPS形式に対応
* カタログのオーバレイが可能

## コンポーネント

このリポジトリは次のコンポーネントを含んでいる。

* `stellar-globe`
  * coreコンポーネント
  * WebGLのシェーダーを含むのはこのレイヤー
* `react-stellar-globe`
  * `stellar-globe`をReactから使うためのラッパー
  * アプリケーション開発はこれを使うとよい
* `react-draggable-dialog`
  * ダイアログボックスのためのReactコンポーネント群
  * ビューワーとは直接関係ないがappから使われている
* `app`
  * HSCのPDR内の`hscMap`というアプリケーションがこれを使っている。

## Python連携

Pythonから`app`のアプリケーションを操作することができる。
`app`はJupyterLabのタブ内で動かすか独自のhttpサーバーで動かすことができる。
