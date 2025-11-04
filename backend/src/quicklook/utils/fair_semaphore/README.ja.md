# FairSemaphore

`FairSemaphore` は待ち行列をFIFOで処理することで、`asyncio.Semaphore` と同じ同時実行制御に加えて取得順序の公平性を保証します。

## 使い方

```python
from quicklook.utils.fair_semaphore import FairSemaphore

sem = FairSemaphore(value=2)

async def worker() -> None:
	async with sem:
		# セマフォを保持している間に安全に処理を行う
		await do_something()

	# 例外が発生した場合でも自動で解放される

# 従来通りの acquire/release も利用可能です
await sem.acquire()
try:
	await do_something()
finally:
	await sem.release()
```
