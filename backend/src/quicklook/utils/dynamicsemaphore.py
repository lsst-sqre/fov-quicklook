import threading
from typing import Optional, Type


import threading
from typing import Optional, Type


class DynamicSemaphore:
    def __init__(self, initial_max_count: int) -> None:
        self.max_count: int = initial_max_count
        self.permits_acquired: int = 0
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def acquire(self) -> None:
        with self.lock:
            while self.permits_acquired >= self.max_count:
                self.condition.wait()
            self.permits_acquired += 1

    def release(self) -> None:
        with self.lock:
            if self.permits_acquired > 0:
                self.permits_acquired -= 1
                self.condition.notify()
            else:
                raise ValueError("release() が acquire() より多く呼び出されました")

    def set_max_count(self, new_max_count: int) -> None:
        with self.lock:
            self.max_count = new_max_count
            self.condition.notify_all()

    # コンテキストマネージャーのメソッドを追加
    def __enter__(self) -> 'DynamicSemaphore':
        self.acquire()
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback) -> None:
        self.release()
