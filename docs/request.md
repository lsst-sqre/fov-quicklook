* こまめにgit commitしてください。

* ./src以下のコードの次の観点でレビューしてください。
  * デッドロックが発生しないか
    * 正常系では問題なく動作することは確認済みですが、思わぬところで例外が起きた時にデッドロックに陥らないか
  * リソースリークが発生しないか
    * 解放し忘れのリソースがないか
    * Generatorを途中でexitした場合、generatorが必ず解放されるか
      * `contextmanager.closing`を積極的に使用しても良いだろう。
  * ↓のファイルリストを順にチェックし終わったものはチェックしcommitしてください。

## レビュー対象ファイルリスト

* [x] `./src/quicklook/comm/test_coordinator_generator.py`
* [x] `./src/quicklook/comm/types.py`
* [x] `./src/quicklook/comm/coordinator.py`
* [x] `./src/quicklook/comm/rpc_worker.py`
* [x] `./src/quicklook/comm/__init__.py`
* [x] `./src/quicklook/comm/generator.py`
* [ ] `./src/quicklook/frontend/api/storage_explorer.py`
* [ ] `./src/quicklook/frontend/api/use_route_names_as_operation_ids.py`
* [ ] `./src/quicklook/frontend/api/get_tile.py`
* [ ] `./src/quicklook/frontend/api/health.py`
* [ ] `./src/quicklook/frontend/api/get_fits_header.py`
* [ ] `./src/quicklook/frontend/api/openapi.py`
* [ ] `./src/quicklook/frontend/api/compression.py`
* [ ] `./src/quicklook/frontend/api/app.py`
* [ ] `./src/quicklook/frontend/api/get_fits_file.py`
* [ ] `./src/quicklook/frontend/api/deps.py`
* [ ] `./src/quicklook/frontend/api/visits.py`
* [ ] `./src/quicklook/frontend/api/quicklooks.py`
* [ ] `./src/quicklook/frontend/api/systeminfo.py`
* [ ] `./src/quicklook/frontend/api/__main__.py`
* [ ] `./src/quicklook/frontend/api/cache_entries.py`
* [ ] `./src/quicklook/frontend/api/staticassets.py`
* [ ] `./src/quicklook/types.py`
* [ ] `./src/quicklook/db/test_db.py`
* [ ] `./src/quicklook/db/session.py`
* [ ] `./src/quicklook/db/__init__.py`
* [ ] `./src/quicklook/db/models.py`
* [ ] `./src/quicklook/coordinator/api/types.py`
* [ ] `./src/quicklook/coordinator/api/app.py`
* [ ] `./src/quicklook/coordinator/api/__main__.py`
* [ ] `./src/quicklook/coordinator/housekeeping/test_housekeeping.py`
* [ ] `./src/quicklook/coordinator/housekeeping/__init__.py`
* [ ] `./src/quicklook/coordinator/create_quicklook/test_create_quicklook.py`
* [ ] `./src/quicklook/coordinator/create_quicklook/__init__.py`
* [ ] `./src/quicklook/coordinator/create_quicklook/generate_single_fits_tiles_coordinator.py`
* [ ] `./src/quicklook/utils/geom/__init__.py`
* [ ] `./src/quicklook/utils/stacklib/test_stacklib.py`
* [ ] `./src/quicklook/utils/stacklib/__init__.py`
* [ ] `./src/quicklook/utils/timer/test_timer.py`
* [ ] `./src/quicklook/utils/timer/__init__.py`
* [ ] `./src/quicklook/utils/timeit/__init__.py`
* [ ] `./src/quicklook/utils/s3/__init__.py`
* [ ] `./src/quicklook/utils/fitsheader/__init__.py`
* [ ] `./src/quicklook/utils/multiprocessing_coverage_compatible.py`
* [ ] `./src/quicklook/utils/websocket.py`
* [ ] `./src/quicklook/utils/imap_unordered_threadpool.py`
* [ ] `./src/quicklook/utils/iterutils/test_iterutils.py`
* [ ] `./src/quicklook/utils/iterutils/__init__.py`
* [ ] `./src/quicklook/utils/numpyutils/__init__.py`
* [ ] `./src/quicklook/utils/exclude_cached_properties_from_pickle/__init__.py`
* [ ] `./src/quicklook/utils/exclude_cached_properties_from_pickle/test_exclude_cached_properties_from_pickle.py`
* [ ] `./src/quicklook/utils/rtree/test_rtree.py`
* [ ] `./src/quicklook/utils/rtree/__init__.py`
* [ ] `./src/quicklook/utils/async_process_generator/test_async_process_generator.py`
* [ ] `./src/quicklook/utils/async_process_generator/__init__.py`
* [ ] `./src/quicklook/utils/pipeline/__init__.py`
* [ ] `./src/quicklook/utils/pipeline/test_pipeline.py`
* [ ] `./src/quicklook/utils/fair_semaphore/__init__.py`
* [ ] `./src/quicklook/utils/fair_semaphore/test_fair_semaphore.py`
* [ ] `./src/quicklook/utils/hash_utils/__init__.py`
* [ ] `./src/quicklook/utils/hash_utils/test_hash_utils.py`
* [ ] `./src/quicklook/utils/http_request.py`
* [ ] `./src/quicklook/utils/fits/test_fits.py`
* [ ] `./src/quicklook/utils/fits/__init__.py`
* [ ] `./src/quicklook/utils/ttlcache/test_ttlcache.py`
* [ ] `./src/quicklook/utils/ttlcache/__init__.py`
* [ ] `./src/quicklook/utils/broadcast/test_broadcast.py`
* [ ] `./src/quicklook/utils/broadcast/__init__.py`
* [ ] `./src/quicklook/utils/zstd.py`
* [ ] `./src/quicklook/utils/throttle/__init__.py`
* [ ] `./src/quicklook/utils/throttle/test_throttle.py`
* [ ] `./src/quicklook/logging.py`
* [ ] `./src/quicklook/dev/psstat.py`
* [ ] `./src/quicklook/dev/commapp.py`
* [ ] `./src/quicklook/dev/debuglog.py`
* [ ] `./src/quicklook/dev/run_uvicorn.py`
* [ ] `./src/quicklook/config/__init__.py`
* [ ] `./src/quicklook/tileinfo/test_tileinfo.py`
* [ ] `./src/quicklook/tileinfo/__init__.py`
* [ ] `./src/quicklook/generator/merge_single_tile_fits.py`
* [ ] `./src/quicklook/generator/transfer_tiles.py`
* [ ] `./src/quicklook/generator/api/app.py`
* [ ] `./src/quicklook/generator/api/__main__.py`
* [ ] `./src/quicklook/generator/retry_on_error.py`
* [ ] `./src/quicklook/generator/generate_single_fits_tiles.py`
* [ ] `./src/quicklook/generator/iteratetiles.py`
* [ ] `./src/quicklook/generator/generator_assignment.py`
* [ ] `./src/quicklook/generator/preprocess_ccd/isr.py`
* [ ] `./src/quicklook/generator/preprocess_ccd/__init__.py`
* [ ] `./src/quicklook/generator/preprocess_ccd/test_preprocess_ccd.py`
* [ ] `./src/quicklook/generator/transfer_fits_headers.py`
* [ ] `./src/quicklook/generator/test_generate_single_fits_tiles.py`
* [ ] `./src/quicklook/scripts/bootstrap_db.py`
* [ ] `./src/quicklook/object_storage/__init__.py`
* [ ] `./src/quicklook/job/test_job_status_printer.py`
* [ ] `./src/quicklook/job/local_storage.py`
* [ ] `./src/quicklook/job/status.py`
* [ ] `./src/quicklook/job/job.py`
* [ ] `./src/quicklook/job/priority.py`
* [ ] `./src/quicklook/job/test_job_local_storage.py`
* [ ] `./src/quicklook/job/shared_large_status.py`
* [ ] `./src/quicklook/job/status_printer.py`
* [ ] `./src/quicklook/job/watcher.py`
* [ ] `./src/quicklook/rpc/types.py`
* [ ] `./src/quicklook/rpc/server.py`
* [ ] `./src/quicklook/rpc/client.py`
* [ ] `./src/quicklook/rpc/test_rpc.py`
* [ ] `./src/quicklook/rpc/__init__.py`
* [ ] `./src/quicklook/rpc/lifespan.py`
* [ ] `./src/quicklook/rpc/queue.py`
* [ ] `./src/quicklook/devserver.py`
* [ ] `./src/quicklook/datasource/types.py`
* [ ] `./src/quicklook/datasource/dummy_datasource/test_dummy_datasource.py`
* [ ] `./src/quicklook/datasource/dummy_datasource/__init__.py`
* [ ] `./src/quicklook/datasource/butler_datasource/butlerutils.py`
* [ ] `./src/quicklook/datasource/butler_datasource/test_butler_datasource.py`
* [ ] `./src/quicklook/datasource/butler_datasource/retrieve_data.py`
* [ ] `./src/quicklook/datasource/butler_datasource/__init__.py`
* [ ] `./src/quicklook/datasource/butler_datasource/instrument.py`
* [ ] `./src/quicklook/datasource/__init__.py`