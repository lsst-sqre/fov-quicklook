from pathlib import Path
from typing import Union
import mineo_fits_decompress_c # type: ignore


def decompressed_bytes(filename: Union[str,Path],  n_threads:int = 8) -> bytes:
    try:
        return mineo_fits_decompress_c.decompressed_fits(str(filename), n_threads)
    except RuntimeError as e:
        raise RuntimeError(f'Error in decompressed_bytes: {e}, file={filename}, n_threads={n_threads}')
