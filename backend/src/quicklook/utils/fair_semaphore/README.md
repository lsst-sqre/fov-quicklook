# FairSemaphore

`FairSemaphore` guarantees fairness in acquisition order in addition to the same concurrency control as `asyncio.Semaphore` by processing the wait queue in FIFO order.

## Usage

```python
from quicklook.utils.fair_semaphore import FairSemaphore

sem = FairSemaphore(value=2)

async def worker() -> None:
	async with sem:
		# Safely perform processing while holding the semaphore
		await do_something()

	# Automatically released even if an exception occurs

# Traditional acquire/release are also available
await sem.acquire()
try:
	await do_something()
finally:
	await sem.release()
```
