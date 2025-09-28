# for-quicklook

## 概要

このアプリケーションはLSST Camの画像データを高速に表示するためのものである。
LSST Camから得られる画像は１ショット189個のFITSファイルからなり、合計で(非圧縮時には)12GB弱のサイズがある。
これらのデータを数秒以内に任意の倍率で表示可能なタイル形式に変換する。

このアプリケーションはk8sクラスターで動くことが前提で、ノード間の性能に差があるかもしれない。

## コンポーネント

このアプリケーションはいくつかのプロセスがTCP通信で協調して動作する。
通信の主体を単位にコンポーネントを挙げる。

* coordinator
  * generatorに対しタイル生成の指示をする。
  * システムで1つだけ動く
* database
  * 生成中のタイル・生成済みのタイルの情報を保持する。
  * システムで1つだけ動く
* generator
  * coordinatorからの指示に従いタイル生成を行う
  * 生成したタイルはオブジェクトストレージに保存する
  * システムで複数動く
* frontend
  * ユーザーからのリクエストに応じてタイルを取得・合成しユーザーへ返す。
  * システムで複数動く

## タイル生成の流れ

タイル生成は`(exposure, dataType)`の組み合わせて指定される`quicklook`単位で行う。1つの`quicklook`には200ほどのFITSファイルが含まれる。

* 初期フェーズ
  * frontendがユーザーからのリクエストを受ける
  * frontendがcoordinatorに`quicklook`の作成の依頼を転送

* GenerateSingleFitsTilesフェーズ
  * coordinatorがgeneratorにタイル生成を指示
    * coordinatorはどのFITSをどのgeneratorに割り当てるかを決定する

      ここは工夫の必要な場所でgeneratorには性能のばらつきがあり、一向に処理が進まないgeneratorが実際にいる。
      そのため、最初に全FITSをgeneratorに割り当てるのではなく動的にスケジュールする。
      詳しくは[こちら](./dynamic-dispatch.ja.md)。
    
    * generatorは分担したFITSファイルをタイル化する
      * このフェーズが終わるとユーザーはプレビューを表示できるようになる
        * ただし`/dev/shm`などを使う必要はなく単に`emptyDir`に保存する（ここに対する書き込みはkernelのバッファリングが効くはずなので非常に重いということはないはず）

* MergeSingleFitsTilesフェーズ
  * coordinatorがgeneratorにタイルのマージを指示
    * coordinatorはどのgeneratorがどのタイルを持っているかを把握している。
  * 1つのタイルが複数のFITSファイルから生成されることがあり、それらをgenerator間でデータをやり取りしてマージする
  * マージが終わった後SingleFitsTilesを削除する

* TransferPackedTilesフェーズ
  * coordinatorはgeneratorに圧縮・アップロードの指示
    * １タイル１オブジェクトだとオブジェクト数が多くなりすぎるので、4x4ほどのタイルをまとめて1つのオブジェクトにする
    * まとめたオブジェクトをオブジェクトストレージにアップロードする
  * アップロードが終わったあとPackedTilesを削除する
  
## 状態管理

* このアプリケーションはk8s上で動作しているので各コンポーネント（特にgenerator）がメモリ圧迫などでしばしばプロセスが再起動されることを前提にする。
* アプリケーション全体のグローバルな状態のうち永続化する必要があるものはdatabaseに、それ以外はcoordinatorのメモリ上に保持する。

### coordinator内メモリ

* 処理中のjob
* 処理リクエスト

### データベース

データベースにはcoordinatorが異常終了したときに復旧するために必要な情報を保存する。

* quicklookについて
  * プロセス中のもの
    * coordinatorが終了したときに中途半端なデータを削除するために必要
  * プロセス済みのもの
    * 以下を記録
      * サイズ合計
      * 生成日時

## リクエストキュー

* ユーザーがページを開くとそのvisitのリクエストがリクエストキューに入る
* リクエストエントリーは次のような情報を持つ
    ```python
    @dataclass
    class RequestEntry:
        visit: VisitName
        vote: int
        first_request: datetime
    ```
* `vote`, `- first_request`大きい順に処理スロットが空いたら処理を開始する。
  * つまり、投票の多いもの、同じ投票数なら古いものから順に処理を開始する。
  * 投票はページを開くと1増え、ページから去ると1減る。
* `generate_single_fits_tile`, `merge_tiles`など処理それぞれに`semaphore`を設けて同時実行数を制限する。

### 実装

処理スロットが空いたタイミングでrequest queueで一番優先順位の高いものをpushする。
処理スロットが空くのを検知するには、