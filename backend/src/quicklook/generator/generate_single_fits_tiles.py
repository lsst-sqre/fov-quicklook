import contextlib
import multiprocessing
import queue
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Generator, Iterable, cast

import quicklook.mylogging
from quicklook.comm.generator import GeneratorIdInitializer
from quicklook.config import config
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat, PreProcessedCcd, preprocess_ccd
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue, Tile
from quicklook.utils.geom import BBox
from quicklook.utils.imap_unordered_threadpool import imap_unordered_threadpool
from quicklook.utils.timer import Timer

logger = quicklook.mylogging.getLogger(__name__)

ds = get_datasource()

# ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
# ローカルFSからの読み込みは非常に高速なため、制限なしでは全CCDが
# 一度にダウンロードされてtmpディレクトリとメモリを圧迫する。
_download_semaphore_size = config.generator_max_concurrent_ccds_per_job + 2


@dataclass
class GenerateSingleFitsTilesProgress:
    ccd_name: CcdName
    progress: Progress


@dataclass
class CcdMetadata:
    ccd_name: CcdName
    image_stat: ImageStat
    amps: list[AmpMetadata]
    bbox: BBox


def _initialize_pool_worker(initializers: list[Callable[[], ContextManager]]) -> None:
    """multiprocessing.Pool用のワーカー初期化関数"""
    global _pool_exit_stack
    _pool_exit_stack = ExitStack()
    for init in initializers:
        _pool_exit_stack.enter_context(init())


_pool_exit_stack: ExitStack | None = None


def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    with tempfile.TemporaryDirectory() as tmpdir, multiprocessing.Manager() as manager:
        q = cast(
            queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata | None],
            manager.Queue(),
        )

        # ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
        # download()でacquire → _process_ccd()のunlink後にrelease。
        # Manager経由で作成し、プロセス間で共有可能にする。
        download_sem = manager.Semaphore(_download_semaphore_size)

        def ccd_paths():
            with ThreadPoolExecutor(2) as executor:
                for path in imap_unordered_threadpool(executor, download, refs, max_in_flight=2):
                    yield path

        def download(ref: CcdDataRef):
            download_sem.acquire()
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd_name, progress=Progress(4, 1)))
            data_bytes = ds.get_data_sync(ref)
            outpath = Path(tmpdir) / f"{ref.ccd_name}.fits"
            outpath.write_bytes(data_bytes)
            logger.info("Downloaded %s (%d bytes)", ref.ccd_name, len(data_bytes))
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd_name, progress=Progress(4, 2)))
            return (ref, outpath)

        def main():
            try:
                initializers = [GeneratorIdInitializer()]
                with multiprocessing.Pool(
                    config.generator_max_concurrent_ccds_per_job,
                    initializer=_initialize_pool_worker,
                    initargs=(initializers,),
                ) as pool:
                    # _process_ccd は CcdMetadata を q に直接入れるため、
                    # pool.imap_unordered の戻り値は使わない。
                    # ただし全タスク完了を待つ必要があるのでイテレータを消費する。
                    for _ in pool.imap_unordered(
                        _process_ccd,
                        (
                            ProcessCcdArgs(
                                job,
                                ref,
                                path,
                                q,  # type:ignore
                                download_sem,
                            )
                            for ref, path in ccd_paths()
                        ),
                    ):
                        pass
            finally:
                q.put(None)  # type: ignore

        with ThreadPoolExecutor(1) as executor:
            fut = executor.submit(main)
            while msg := q.get():
                yield msg
            fut.result()


@dataclass
class ProcessCcdArgs:
    job: Job
    ref: CcdDataRef
    path: Path
    progress: queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata]
    download_sem: Any  # multiprocessing.Manager().Semaphore() proxy


def _process_ccd(args: ProcessCcdArgs):
    try:
        ppccd = preprocess_ccd(args.ref, args.path)
        args.progress.put(
            GenerateSingleFitsTilesProgress(
                ccd_name=ppccd.data_ref.ccd_name,
                progress=Progress(4, 3),
            )
        )
    finally:
        args.path.unlink(missing_ok=True)
        args.download_sem.release()

    generate_tiles(ppccd, args.job)
    args.progress.put(
        GenerateSingleFitsTilesProgress(
            ccd_name=ppccd.data_ref.ccd_name,
            progress=Progress(4, 4),
        )
    )

    args.job.local_storage.fits_header.save(args.ref.ccd_name, ppccd.headers)

    # CcdMetadata を q に直接入れる。
    # pool.imap_unordered 経由で main() に返して q.put する方式では、
    # imap_unordered の入力ジェネレータがブロックしている間に
    # main() の forループも停止し、CcdMetadata が q に入らないことがある。
    ccd_metadata = CcdMetadata(
        ccd_name=ppccd.data_ref.ccd,
        image_stat=ppccd.stat,
        amps=ppccd.amps,
        bbox=ppccd.bbox,
    )
    args.progress.put(ccd_metadata)


def generate_tiles(
    ppccd: PreProcessedCcd,
    job: Job,
):
    storage = job.local_storage

    def cb(tile: Tile):
        storage.single_fits_tile.save(ppccd.data_ref.ccd, tile)

    iterate_tiles(ppccd, cb)


if False:
    # これは以前使っていた並列度の低い遅い実装

    import threading

    def generate_single_fits_tiles(
        job: Job,
        ref: CcdDataRef,
    ):
        yield (progress := Progress(total=3))

        data_bytes = ds.get_data_sync(ref)
        yield progress.update()

        try:
            with _bytes_to_file(data_bytes) as path:
                ppccd = preprocess_ccd(ref, path)
                yield progress.update()

            generate_tiles(ppccd, job)
            yield progress.update()

            job.local_storage.fits_header.save(ref, ppccd.headers)

            yield ReturnValue(
                CcdMetadata(
                    ccd_name=ppccd.data_ref.ccd,
                    image_stat=ppccd.stat,
                    amps=ppccd.amps,
                    bbox=ppccd.bbox,
                )
            )
        finally:
            # 遅いgeneratorでこの関数が実行された時
            # coordinatorのcleanupの後にまだこの関数が実行されている可能性がるので
            # ここでもcleanupする。
            #
            # from threading import Timer
            # なぜかPython標準のTimerを使うとgenerator全体が停止してしまう。
            Timer(600, job.local_storage.clear_all).start()

    @contextlib.contextmanager
    def _bytes_to_file(data: bytes, dir=config.fitsio_tmpdir):
        dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dir) as f:
            f.write(data)
            f.flush()
            yield Path(f.name)
