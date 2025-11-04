# Timer

Pythonの標準の`threading.Timer`は新しくタイマーを設定するたびに新しくスレッドが作成される。
多数のタイマーを同時に実行すると、スレッドの数が増えすぎてしまうので1つのスレッドで複数のタイマーを管理する仕組みを実装する。

## 実装

* １つのスレッドが複数のタイマーを管理する。
* 管理用のスレッドは初回呼び出しの時に作成される。
* この管理用のスレッドは１秒に1回登録されたタイマーをチェックし、時間が来たタイマーを実行する。
* チェックの間隔は変更可能


## 使い方

Python の `threading.Timer` と互換のインターフェースを提供するが、利用時には `start()` を呼び出してタイマーを登録する必要がある。

```python
from quicklook.utils.timer import Timer

timer = Timer(30, print, args=("hello",))
timer.start()

# 実行前に取り消したい場合
timer.cancel()
```

登録済みのタイマーは `cancel()` で取り消せる。処理完了の判定は `finished` プロパティ、実行待ちの判定は `is_alive()` で行える。

## API

### Timer

```
Timer(interval: float, function: Callable[..., Any], args: tuple[Any, ...] | None = None,
	kwargs: dict[str, Any] | None = None)
```

* `interval` 秒後に `function(*args, **kwargs)` が 1 回だけ実行される。
* `start()` は 1 度だけ呼び出せる。2 度目以降は `RuntimeError` になる。
* `cancel()` は実行前であれば処理を取り消す。
* `is_alive()` はタイマーが実行待ちかどうかを返す。
* `finished` は実行済み (もしくはキャンセル済み) かどうかを返す読み取り専用プロパティ。

### チェック間隔の変更

管理スレッドがタイマーを確認する間隔は既定で 1.0 秒。`set_check_interval()` で変更できる。

```python
from quicklook.utils.timer import set_check_interval

set_check_interval(0.05)
```

設定はプロセス全体で共有され、既に動作している管理スレッドにも即座に反映される。テストなどで短時間に多数のタイマーを扱う場合に役立つ。