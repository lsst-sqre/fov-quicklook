## 今回のタスク

coordinator, generatorのシステム状況を取得するAPIの整備。
各コンテナ内で以下のようにして取得する。

```bash
# 現在のメモリ使用量（bytes）
cat /sys/fs/cgroup/memory.current

# メモリ上限（bytes）※"max" は無制限
cat /sys/fs/cgroup/memory.max

# CPU累積使用時間（microseconds）
cat /sys/fs/cgroup/cpu.stat
# 出力例:
# usage_usec 123456789
# user_usec  98765432
# system_usec 24691357

# CPU上限（quota）と period
cat /sys/fs/cgroup/cpu.max
# 出力例:
# 50000 100000
# → quota=50000μs, period=100000μs → 0.5 CPU (= 50%)
# "max" は無制限
```

各コンテナについて↓を取得する。

```python
@dataclass
class ContainerStatus:
    container_name: str
    memory_max: int
    memory_current: int
    cpu_max: int
    cpu_current: int
    uptime: float
```

* frontendに`/api/status`エンドポイントを追加
  * 自コンテナのステータスとcoordinatorに問い合わせて得られたcoordinator, generatorのステータスを返す
* coordinatorに`/status`エンドポイントを追加
  * 自コンテナのステータスとgeneratorのステータスを返す
* generatorに`/status`エンドポイントを追加
  * 自コンテナのステータスを返す

* coordinatorからgeneratorへのアクセス方法を知るのは`src/quicklook/comm`を参照
* frontendからcoordinatorへのアクセスは`src/quicklook/frontend/api/quicklooks.py`を参照
* 値の取得に失敗したら0を返す

* frontendでは次のようなデータを返す

```python
@dataclass
class SystemStatus:
    frontend: ContainerStatus
    coordinator: ContainerStatus
    generators: dict[GeneratorId, ContainerStatus]
```

* テストも作成する。
* coordinatorでは複数のノードに対してステータスを取得する必要がこれは並列に行う
