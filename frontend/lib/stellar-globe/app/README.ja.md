## 概要

JupyterLiteの登場によりJupyterはクライアントサイドで完結する環境で動くようになった。
JupyterLiteはinteractiveなmatplotlib, numpy, astropyなどが動作する。

hscMap4に存在していた、グラフ表示機能、ウインドウ機能などをJupyterの機能を利用することで実現できる。
Jupyterの機能で実現できる機能はhscMap本体には含めないこととしコード量削減をはかる。

## 設計

* Reduxを使用
  * 自動的にJupyterから呼び出せるAPIが整備される。
  * （RTKにより以前に比べRedux関連のコード記述量が減っている）

## 型情報のエクスポート

* RTKによって作られる方は`vite-dts-plugin`を使用して、型情報をエクスポートすることはできなかった。
* `types/index.d.ts`は手動で作っている。
* ↑の型は`export.ts`で矛盾がないかコンパイル時にチェックする。
      
## 型チェッカーの更新

```bash
npm run refresh-types
```

## TODO

* [x] 右クリック
  * [x] SIMBAD
* [x] カタログdialog
* [ ] ~~カタログクリックイベント~~
* [x] Jupyter Region
* [ ] 位置、階調同期Dock


## Trouble Shooting

#### typesVersions in package.json

https://www.npmjs.com/package/typescript-subpath-exports-workaround
