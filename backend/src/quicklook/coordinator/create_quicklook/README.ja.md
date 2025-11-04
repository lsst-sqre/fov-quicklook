# GenerateSingleFitsTiles Coordinator

## 概要

このモジュールは、複数のジェネレータ（Generator Pod）にCCDの処理を動的に割り当て、FITSデータからタイルを生成する協調処理を行います。

## 主要な設計思想

### 動的ワークロードバランシング

各ジェネレータのパフォーマンスは均一ではありません：
- k8sのPodとして動作し、ノードの負荷状況により性能が変動
- 一部のジェネレータが極端に遅くなる可能性がある
- 静的な事前割り当てではボトルネックが発生

この問題に対処するため、**2段階の動的割り当て戦略**を採用しています。

## 2段階処理アルゴリズム

### Phase 1: 初期ディスパッチ

すべてのCCDを各ジェネレータに1回ずつsubmitします。

```
remaining_ccds = [ccd1, ccd2, ..., ccdN]
↓
各generatorに空きができたら順次submitしていく
```

**特徴**：
- 各ジェネレータは`config.generator_max_concurrent_ccds_per_job`個のCCDを同時処理
- 初期バッチで複数のCCDを同時にsubmit（コールドスタート対策）
- 高速なジェネレータがより多くのCCDを処理

### Phase 2: 再ディスパッチ（Resubmit）

すべてのCCDが一度submitされた後も、未完了のCCDを継続的に再submitします。

```
while 未完了のCCDが存在する:
    最も古くsubmitされた未完了CCDを取得
    ↓
    空きができたgeneratorに再submit
    ↓
    より高速なgeneratorが処理を引き継ぐ
```

**利点**：
- 遅いジェネレータで処理中のCCDを、速いジェネレータでも並行処理
- 最初に完了したメタデータを採用（重複実行しても問題なし）
- 極端に遅いジェネレータがボトルネックにならない

**例**：
```
Generator A: 処理速度 10 ccd/分
Generator B: 処理速度 1 ccd/分（極端に遅い）

Phase 1後:
- Generator A: ccd1, ccd2, ... ccd100 → すべて完了
- Generator B: ccd101 → まだ処理中（残り50分）

Phase 2:
- Generator A: 空きができたのでccd101を再submit
- Generator A: ccd101を1分で完了 ✓
- Generator B: ccd101の処理がまだ続いているが結果は無視される
```

## データ構造

### 状態管理

```python
remaining_ccds: deque[CcdDataRef]
    # Phase 1で使用。まだ一度もsubmitされていないCCD

submitted_ccds: list[CcdDataRef]
    # submitした順序を保持。Phase 2で未完了CCDを探索するために使用

phase2_index: int
    # Phase 2でのラウンドロビン用インデックス

ccd_metadata_dict: dict[CcdName, CcdMetadata]
    # 完了したCCDのメタデータ。最初に完了したもののみ保存

ccd_generator_map: dict[CcdName, GeneratorId]
    # どのgeneratorが最初に完了したかを記録
```

### 処理フロー

```python
async def get_next_ccd_to_submit() -> CcdDataRef | None:
    # Phase 1: remaining_ccdsから取得
    if remaining_ccds:
        ccd_ref = remaining_ccds.popleft()
        submitted_ccds.append(ccd_ref)
        return ccd_ref
    
    # Phase 2: 未完了CCDをラウンドロビンで取得
    for offset in range(len(submitted_ccds)):
        idx = (phase2_index + offset) % len(submitted_ccds)
        ccd_ref = submitted_ccds[idx]
        if ccd_ref.ccd_name not in ccd_metadata_dict:
            phase2_index = (idx + 1) % len(submitted_ccds)
            return ccd_ref
    
    # すべて完了
    return None
```

**重要**: Phase 2では同じCCDが複数のgeneratorで同時に処理されることを**許可**します。ラウンドロビンにより、未完了のCCDを順番に繰り返しsubmitし、高速なgeneratorが積極的に処理できるようにします。

## 終了条件

すべてのCCDのメタデータが取得できたら、各workerに終了シグナル（`None`）を送信します。

```python
async def should_send_termination_signal() -> bool:
    all_completed = len(ccd_metadata_dict) == len(ccd_refs)
    if all_completed and workers_notified < len(generator_list):
        workers_notified += 1
        return True
    return False
```

**重要**: 
- 各workerは独立したRPCストリームを持つため、それぞれに終了シグナルが必要
- `workers_notified`カウンタで重複送信を防止

## 並行処理の同期

すべての状態変更は`asyncio.Lock`で保護されています：

```python
lock = asyncio.Lock()

async with lock:
    # 状態の読み取り・変更
    if remaining_ccds:
        ccd_ref = remaining_ccds.popleft()
        submitted_ccds.append(ccd_ref)
```

これにより、複数のworkerが同時に状態を変更しても競合が発生しません。

## 設定パラメータ

- `config.generator_max_concurrent_ccds_per_job`: 各ジェネレータが同時に処理できるCCD数（デフォルト: 設定による）

## パフォーマンス特性

### 最悪ケースの改善

**従来の実装（Phase 1のみ）**：
```
総処理時間 = max(各generatorの処理時間)
```
極端に遅い1つのgeneratorがボトルネックになる。

**2段階実装（Phase 1 + Phase 2）**：
```
総処理時間 ≈ 総CCD数 / 高速generatorの合計スループット
```
遅いgeneratorの影響を最小化できる。

### トレードオフ

**利点**：
- 遅いgeneratorのボトルネック解消
- 全体の処理時間が大幅に短縮
- 自動的に最適な負荷分散

**コスト**：
- 一部のCCDが重複して処理される（計算リソースの浪費）
- メタデータは最初の完了分のみ採用（後続の結果は破棄）

実環境では、極端に遅いgenerator（k8s nodeの高負荷など）が存在する場合があり、この重複処理のコストは十分に正当化されます。

## 関連モジュール

- `quicklook.rpc.queue.RpcQueue`: 動的なCCD供給のためのキューメカニズム
- `quicklook.generator.generate_single_fits_tiles`: Generator側の処理実装
- `quicklook.comm.coordinator.get_available_generators`: 利用可能なgeneratorの取得
