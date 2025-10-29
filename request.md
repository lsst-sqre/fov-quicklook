## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `frontend/app/src/components/JobList/index.tsx`

  各ジョブのデザインの修正をお願いします。
  現在、ジョブに対する要素の背景が斜めのグラデーションになっています。
  これを修正して縦方向のグラデーションにしてください。

* [x] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`

  現在、とある契機で`scrollIntoView`が呼ばれているがこれが呼ばれる頻度が高すぎる。
  statusListの数が変わった時だけ呼び出すようにしてください。
