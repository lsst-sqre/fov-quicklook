import asyncio
from collections import deque


class OrderedSemaphore:
    """
    A semaphore implementation similar to asyncio.Semaphore but guarantees
    that tasks acquire the lock in the same order as they called acquire.
    """

    def __init__(self, value: int = 1) -> None:
        """
        Initialize a semaphore with the given value.

        Args:
            value: The initial value of the semaphore (default: 1)
        """
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._value = value
        self._waiters: deque[asyncio.Future[None]] = deque()

    def _wake_up_next(self) -> None:
        """Wake up the first waiter in the queue if there is one."""
        while self._waiters:
            waiter = self._waiters[0]
            if not waiter.done():
                waiter.set_result(None)
                return
            self._waiters.popleft()

    async def acquire(self) -> bool:
        """
        Acquire the semaphore, waiting if necessary in order of acquisition.

        Returns:
            Always True (unless an exception is raised)
        """
        while self._value <= 0:
            # Create a waiter and add it to the queue
            waiter = asyncio.get_event_loop().create_future()
            self._waiters.append(waiter)
            try:
                await waiter
            except:
                # If an exception occurs, clean up the waiter from the queue
                if not waiter.done() and waiter in self._waiters:
                    self._waiters.remove(waiter)
                    if self._value > 0 and self._waiters:
                        self._wake_up_next()
                raise

        self._value -= 1
        return True

    def release(self) -> None:
        """
        Release the semaphore, waking up the next waiter if there is one.
        """
        self._value += 1
        self._wake_up_next()

    def locked(self) -> bool:
        """Check if the semaphore is locked."""
        return self._value == 0

    async def __aenter__(self) -> "OrderedSemaphore":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
