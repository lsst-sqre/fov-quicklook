import tqdm
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.types import PreProcessedCcd, Progress, Tile


def test_iterate_tiles(preprocessed_ccd: PreProcessedCcd):

    with tqdm.tqdm() as pbar:

        def cb(tile: Tile, progress: Progress):
            pbar.total = progress.total
            pbar.n = progress.count
            pbar.refresh()

        iterate_tiles(preprocessed_ccd, cb)
