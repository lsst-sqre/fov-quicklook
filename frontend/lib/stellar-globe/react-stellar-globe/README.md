# React Stellar-Globe

* Reactのrender、hookの実行順序
   * 親子、同時に作られる時
      * マウント時
         * 親のrender
         * 子のrender
         * 仮想DOMが出来上がる
         * それに従って実DOMを作成
         * 子コンポーネントuseEffect
         * 親コンポーネントuseEffect
      * アンマウント時
         * 親コンポーネントuseEffect.cleanup
         * 子コンポーネントuseEffect.cleanup

マウント時はuseEffectでglobe操作。
アンマウント時にlayer.release()。layer.releaseは2度呼ばれても問題ないので。

```tsx
<GLobe>
   <GridLayer />
</Globe>
```

のようなことをしたい。
開発モードでは useEffect は２回呼ばれる。
cleanup関数で適切にcleanupしないといけない
