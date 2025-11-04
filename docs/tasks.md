## Incomplete Tasks

* [x] Reduce memory usage
  * Per process < ~0.4GB
  * Idle state
    - 700MB
  - single fits tile generation
    - 20 parallel
      - ~4GB. Can momentarily exceed 5GB
    - 16 parallel
      - ~3GB
    - CPU usage at most ~20
  - merge tile
    - ~1GB
    - 4 parallel
    - ~100MB per process?
  - transfer tile
    - ~1GB
    - 4 parallel
    - ~100MB per process?
* [x] phalanx adjustment
  * [x] storage-prefix
* [x] Highlighting
* [x] FITS file header display
* [x] Verify housekeeping is being called
* [x] Admin page
  * [x] Job list
* [x] Slow pod handling
  * Slow pods should be restarted.
* [x] Bug fixes
  * [x] Post ISR is not processing correctly
* [x] Jobs sometimes never finish
* [ ] Queue page
  * Improve display
* [x] Reduce waiting_user when leaving page
* [x] Liveness/readiness probe
* [x] Support for types other than raw
  ```lsst.daf.butler._exceptions.MissingCollectionError: No collection with name 'LSSTCam/runs/nightlyValidation' found.```

* [ ] Error handling considerations
  * For example, a quicklook becomes in error if a user leaves a page and waiting_user becomes 0.
  * When an error occurs, stage=error and data is deleted, and records are deleted.
  * If you access that page while the error termination process is in progress, `QuicklookMetadata` is in an error state to the client

* [ ] Next time
  * [ ] Change comm heartbeat to websocket
  * [ ] Reuse connections to generators
    * src/quicklook/frontend/api/get_tile.py
    * Create connection object with life_span
    * Consider retry
      * src/quicklook/generator/retry_on_error.py
  * [ ] Security
    * Security measures other than k8s network policy
    * Don't put pickle in object storage

## Connecting with webapp considerations

* Webapp flow
  * Select visit from list
  * currentID changes
  * Request create
  * Watch status via ws
  * Show progress until single fits tile generation is complete
  * quicklook metadata is sent from the same websocket
  * Use it to display tiles

* Frontend flow
  * On create
    * [x] Forward directly to coordinator
  * Status is always via websocket
    * Check if there is an entry with ready=true in DB
    * Monitor stage and wait for it to become generate_single_fits_tiles or later
    * Get quicklook_metadata
    * Display tiles

* Tile generation error handling

* Considerations
  * How to share large objects between coordinator and frontend

    `JobStatus` list is updated frequently but is small in size, so all elements are sent each time, but if it contains large elements, this is not efficient.
    `JobStatus` does not include it, but `ccd_generator_map` and `ccd_metadata_list` should be shared in real-time between coordinator and frontend.

    * Create a `JobSharedLargeStatus` class to achieve this.
    * This class should include `ccd_generator_map` and `ccd_metadata_list`.
    * Make it accessible via `job.shared_large_status`
    * `JobWatcher` handles notifications as with `JobStatus`.
      * Create `asynccontextmanager notify_shared_large_status`, which calls callbacks registered with `on_shared_large_status_change` after exiting.
    * Sharing between coordinator and frontend is done by extending the current way `JobStatusList` is shared.
      * In `src/quicklook/coordinator/api/app.py`
        * Currently coordinator notifies frontend with `JobStatusList` on `/quicklooks/*/status.ws`.
        * `quicklook_status_relay` in `src/quicklook/frontend/api/quicklooks.py` connects to this endpoint.
        * Change this endpoint to `/quicklooks/*/shared_status.ws` and have two types of notifications, `JobStatusList` notification and `JobSharedLargeStatus` notification, through this connection.
        * Use a protocol appropriate for two types of notifications
        * Adapt `quicklook_status_relay` to this and change the name to something appropriate.
        * `JobSharedLargeStatus` notifications are per job. When frontend receives this notification, it updates the information of the corresponding job.
          Frontend clears old entries (keeps at most `config.pipeline_queue_size*2`).

# Completed Tasks
* [x] Management screen
  * Cache viewer
  * DB viewer
* [x] Implementation of sharing large objects between coordinator and frontend

  This is mainly about `src/quicklook/coordinator/api/app.py`, `src/quicklook/coordinator/create_quicklook.py`, `src/quicklook/frontend/api/quicklooks.py`.
  Currently `JobStatus` list is updated frequently but is small in size, so all elements are sent each time, but if it contains large elements, this is not efficient.
  `JobStatus` does not include it, but `ccd_generator_map` and `ccd_metadata_list` should be shared in real-time between coordinator and frontend.

  * Create `JobSharedLargeStatus` class to achieve this.
    * Based on `JobStatus`.
    * This class should include `ccd_generator_map` and `ccd_metadata_list`.
    * Make it accessible via `job.shared_large_status`
  * `JobWatcher` handles notifications as with `JobStatus`.
    * Create `asynccontextmanager notify_shared_large_status` in `Jobwatcher`, which calls callbacks registered with `on_shared_large_status_change` after exiting.
  * Sharing between coordinator and frontend is done by extending the current way `JobStatusList` is shared.
    * In `src/quicklook/coordinator/api/app.py`
      * Currently coordinator notifies frontend with `JobStatusList` on `/quicklooks/*/status.ws`.
      * `quicklook_status_relay` in `src/quicklook/frontend/api/quicklooks.py` connects to this endpoint.
      * Change this endpoint to `/quicklooks/*/shared_status.ws` and have two types of notifications, `JobStatusList` notification and `JobSharedLargeStatus` notification, through this connection.
      * Use a protocol appropriate for two types of notifications
      * Adapt `quicklook_status_relay` to this and change the name to something appropriate.
      * `JobSharedLargeStatus` notifications are per job. When frontend receives this notification, it updates the information of the corresponding job.
        Frontend clears old entries (keeps at most `config.pipeline_queue_size*2`).
* [x] Modify `src/quicklook/coordinator/api/app.py::route_create_quicklook` to only push to pipeline when there is no corresponding entry in DB
* [x] Fix implementation of `src/quicklook/frontend/api/quicklooks.py::{get_quicklook_status,websocket_quicklook_status}`
  * Check if there is an entry with ready=true in DB
  * If yes, return `JobStatus` with `stage='ready'`
  * If not, get from `job_status_list` and return
* [x] Refactor `src/quicklook/coordinator/housekeeping/test_housekeeping.py`
  * This test is not passing. Please fix it.
  * You can completely reset the DB to fix the test. (including deleting the `alembic_version` table)
    * `src/quicklook/scripts/bootstrap_db.py` should include code to reset the DB this way if DB inconsistencies occur.
    * Verify that `src/quicklook/scripts/bootstrap_db.py` works correctly.
* [x] Refactoring around `./src/quicklook/coordinator/create_quicklook.py`
  * Return values from each stage of the pipeline should be a single common object that is passed around
    * Create a dataclass `PipeLineResult` and update its properties in each stage
    * Align the input and output shapes of each stage to eliminate the need to create many similar functions like `select_next_job` and `select_next_job_with_size`.
* [x] Refactoring around `./src/quicklook/object_storage/__init__.py`
  * Please consolidate `import asyncio` at the top of the file.
* [x] Refactoring around `./src/quicklook/coordinator/housekeeping/__init__.py`
  * `_delete_object_storage_sync` should use the async version of `storage.delete_all_sync` to make it an async function.
* [x] Refactoring `src/quicklook/coordinator/test_create_quicklook.py`
  * Reset the state of the `quicklooks` table at the start of tests in this module.
  * Run tests with `./.venv/bin/pytest src/quicklook/coordinator/test_create_quicklook.py -m 'slow'`
* [x] Refactoring around `./src/quicklook/comm`
  * Coordinator does not include coordinator_id in error notifications on error
* [x] Refactoring around `./src/quicklook/coordinator/create_quicklook.py`
  * `_finalize` is always called with `error=True`, so rename to `_finalize_error` and remove the `error` parameter
  * Add `error` status to `JobStatus.stage`.
    * On error, set status to `error`
    * In `src/quicklook/coordinator/api/app.py`, on error, don't delete from `jobs` immediately, but wait 30 seconds before deleting
  * Treat `_transfer_fits_headers` as a pipeline stage on the same level as `_merge_tiles`.
    * Also accumulate the `uploaded_size` of `_transfer_fits_headers` with that of `transfer_tiles` and record it in the DB entry information.
  * Run tests with `./.venv/bin/pytest src/quicklook/coordinator/test_create_quicklook.py -m 'slow'`
* [x] Refactoring around `./src/quicklook/object_storage/__init__.py`
  * Add async versions of methods to `VisitObjectStorage`.
    * S3-related methods are synchronous functions, and if they take time, async environment will block the entire system. Therefore, it is necessary to add async versions of methods to enable async execution.
  * Rename existing sync methods that access object storage to have `_sync` suffix.
  * Async versions run sync versions in separate threads.
  * Find callers of existing methods and replace with async versions if called in async environments
* [x] Refactoring around `./src/quicklook/config/__init__.py`
  * Change default value of `max_object_storage_usage` to 45GB
* [x] Refactoring around `./src/quicklook/coordinator/housekeeping/__init__.py`
  * Create test code
    * You can fully reset the DB at the start of the test
* [x] Comm refactoring
  * `./src/quicklook/comm` contains the processing for coordinator and generator cooperation.
  * Currently, the generator periodically registers itself to the coordinator, and processing is added to this.
  * Coordinator assigns a uuid to itself at startup
  * Generator receives this uuid from coordinator on first registration
  * Generator sends this uuid to coordinator during periodic registration.
  * Coordinator rejects registration if the uuid is different from its own uuid (this means the coordinator has restarted.)
  * Generator should shut down in this case (using `_shutdown` function)
* DB related
  * Development environment
    * `make db/docker` starts the development DB.
    * DB connection information is described in `src/quicklook/config/__init__.py`.
  * [x] Introduce async version of SQLAlchemy2
    * See schema below
  * [x] Introduce alembic
    * DB-related tasks in `Makefile` can be managed via `db/*`.
* Register quicklook information to DB
  * [ ] Implement `src/quicklook/coordinator/create_quicklook.py`.
    * Create a record with `ready=false` at initial creation of quicklook, set to `ready=true` when complete. Set `disk_usage` at this time as well.
    * If an error occurs, delete the record.
      * Add an `error` parameter to the `_finalize` function and handle it there. This would be a good approach.
* [x] Processing additions to `src/quicklook/coordinator/create_quicklook.py`
  * In `_finalize`, also delete data in object storage on error.
    * Reference `job.object_storage`.
    * Currently there is no method in `VisitObjectStorage` to delete related object storage entries. It will be necessary to implement a method using `delete_objects_by_prefix`.
* [x] Housekeeping
  * Currently `quicklooks` records keep increasing, and data also accumulates in object storage
  * At some point, data must be selected and deleted. Implement this as an `async` function:
    * Add a configuration for object storage usage limit in `src/quicklook/config/__init__.py`
    * Current object storage usage can be confirmed with `sum(quicklooks.disk_usage)` in DB.
    * Implement in `src/quicklook/coordinator/housekeeping/__init__.py`
    * When this function is called, it performs the following:
      * Select one `quicklooks` entry to delete
        * Separate the function that selects this entry
        * For now, select one in order of least access within the last week, (if the same, oldest `created_at` first)
      * Set to `ready=false`
      * Delete object storage data associated with that entry.
      * Delete the DB entry after object storage data deletion is complete.
      * Repeat until the total of `disk_usage` is less than the configured value.
      * It's good to separate the function that deletes one entry
    * Bulk deletion of object storage entries will likely take time. Functions that include it should have a sync version and async versions should run it in a separate thread
* [x] Startup cleanup
  * Implement a function for this in `src/quicklook/coordinator/housekeeping/__init__.py`.
  * This function deletes associated data if there are `quicklooks` entries with `ready=false` and deletes the DB entry after that is complete.
  * Functions prepared in the housekeeping described above can be used
* [x] Prepare DB bootstrap script
  * Create a script that runs alembic migrations.
  * If this fails, delete all tables in the DB, delete all objects starting with `config.s3_tile_key_prefix` in object storage, and re-run the migration
* [x] Have `JobStatus` hold `ccd_generator_map` from `src/quicklook/coordinator/create_quicklook.py`.
* [x] Implement fits_header and metadata object storage upload feature (`transfer_metadata`)
  * Implement as a task at the same level as `generate_single_fits_tiles`, `merge_fits_tiles`, `transfer_fits_tiles`.
  * Performed after `merge_fits_tiles`
  * One fits header is obtained per CCD.
  * Save to local storage in `src/quicklook/generator/generate_single_fits_tiles.py` with `job.local_storage.fits_header.save(ref, ppccd.headers)`.
  * Upload those processed on this node to object storage via `job.object_storage`, referring to `_iter_primary_pos(job: Job)` in `src/quicklook/generator/merge_single_tile_fits.py`. Note that a new method for uploading fits headers needs to be added to `VisitObjectStorage`.
  * Return the total uploaded.
* [x] Save quicklook metadata to object storage
  * Metadata for each CCD is collected in `_generate_single_fits_tiles` in `src/quicklook/coordinator/create_quicklook.py`.
  * Save this list to object storage.

## DB Schema

```sql
create table quicklooks ( 
  visit_name: string primary key,
  job_id: string not null unique,
  disk_usage: integer not null,
  created_at: datetime not null
);

create table accesses (
  visit_name: string references quicklooks(visit_name),
  accessed_at: datetime not null
);
```
