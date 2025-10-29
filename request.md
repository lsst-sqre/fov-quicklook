## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `frontend/app/src/pages/Home/Viewer/CompactStatus/index.tsx`のリファクタリング

  * `showMemoryUsageInCompactStatus`でmemory usageかunrecoverable memoryのどちらかを表示するようにしているが、どちらを表示するのではなく、この値でmemory usageを表示するか決めるようにしてください。（unrecoverable memoryは常に表示。）
  memory usageやunrecoverable memoryという表記は長いのでどちらもMem, tooltipで詳しい意味を表示するようにしてください。

  * CPUの割合は現在は`<Progress/>`とテキスト表記どちらも同じになっていますが、ここは分けてください。
  `<Progress/>`は`cpu_max`に対する割合。テキストは１論理CPUの使用時間割合としてください。