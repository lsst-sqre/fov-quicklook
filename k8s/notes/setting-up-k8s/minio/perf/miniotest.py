from typing import Callable
from minio import Minio
import io
import numpy

client = Minio(
    "192.168.13.201:9000",
    access_key="quicklook",
    secret_key="password",
    secure=False,
)


def main():
    random_data = numpy.random.bytes(32 * 1000_000)

    def put_object():
        obj = io.BytesIO(random_data)
        client.put_object(
            "quicklook-tile",
            "sample",
            obj,
            32 * 1000_000,
        )

    timeit("put_object", put_object, 10)


def timeit(label: str, f: Callable, iteration=1):
    import time

    start = time.time()
    for _ in range(iteration):
        print(f"iteration {_}")
        f()
    end = time.time()
    print(f"{label}: {end - start:.3f} sec")


if __name__ == "__main__":
    main()
