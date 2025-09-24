import numpy
import io


def ndarray2npybytes(arr: numpy.ndarray) -> bytes:
    with io.BytesIO() as f:
        numpy.save(f, arr)
        return f.getvalue()


def npybytes2ndarray(b: bytes) -> numpy.ndarray:
    with io.BytesIO(b) as f:
        return numpy.load(f)
