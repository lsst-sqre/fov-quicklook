* 検討
  * [ ] drag中にrenderingが起きると位置が飛ぶ
    * dnd-kitに由来するようだ
      * transformの値がジャンプしている
  * [x] 初回移動まではpositionHintを反映
    * positionHintにright, bottomが指定された場合や、leftが50vwなどの場合に初回移動まではその設定を反映する
  * [x] minmax
    * sizeHintで指定？
    * CSSの指定ができるとよい
  * [ ] タイトルバーにフォーカスが当たってる時に矢印キーを押すとキーボードイベントがstopされない
  * [x] 初期visible=falseの場合
  * [x] hintされている場所がすでに埋まっている場合
  * [x] rememberPosition prop
    * falseの場合、初回表示時にreposition
  * [x] contextにpositionFinderを指定可能に

* Dialog
  * 概要
    * dragできる
    * クリックでz-indexを調整
    * 大きさの決め方
      * 指定なし
        * resizable: false
          * 常に内容により決まる
        * resizable: true
          * マウント時に内容により決まる
          * サイズ変更後はサイズが保持される
          * サイズ変更前は内容により自動で変わる
      * 指定あり
        * width, heightで指定。(ピクセル単位でなくても良い。right, leftの組み合わせでは決められない)
        * resizable: false
          * 指定と内容により決まる (widthだけの指定だと高さが可変になったり。)
        * resizable: true
          * マウント時に指定と内容により決まる
          * 以後の内容の変更によっては変わらない
    * 初期位置の決め方
      * 指定あり
        * マウント時にその値で決める
        * left, top, right, bottomで決める
      * 指定なし
        * マウント時に自動で決める
    * 実装
      * useState({ size, position })
        * positionのみの場合がある

  * props
    * title
    * children
    * resizable: boolean
    * positionHint?
    * size?

* Position = { left, top }
* Size = { width, height }
* Rect = Position & Size

* Resizable
  * props
    * nodeRef
    * rect: Rect | undefined
    * onChange: (rect: Rect) => void
