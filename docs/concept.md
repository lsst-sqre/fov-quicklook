# fov-quicklook

## Overview

This application is designed to display LSST Camera image data at high speed.
Images obtained from the LSST Camera consist of 189 FITS files per exposure and have a total size of approximately 12 GB (when uncompressed).
These data are converted into a tiled format that can be displayed at any magnification within a few seconds.

This application is designed to run on a Kubernetes cluster, and there may be performance differences between nodes.

## Components

This application consists of several processes that work together through TCP communication.
Components are listed based on the communication entities.

* coordinator
  * Instructs generators to generate tiles.
  * Only one runs in the system
* database
  * Maintains information about tiles being generated and already generated tiles.
  * Only one runs in the system
* generator
  * Performs tile generation according to instructions from the coordinator
  * Saves generated tiles to object storage
  * Multiple instances run in the system
* frontend
  * Retrieves and composites tiles in response to user requests and returns them to users.
  * Multiple instances run in the system

## Tile Generation Flow

Tile generation is performed in units of `quicklook`, which is specified as a combination of `(exposure, dataType)`. One `quicklook` contains about 200 FITS files.

* Initial Phase
  * Frontend receives a request from the user
  * Frontend forwards the request to the coordinator for creating a `quicklook`

* GenerateSingleFitsTiles Phase
  * Coordinator instructs generators to generate tiles
    * The coordinator determines which FITS files are assigned to which generators

      This is an area that requires careful consideration, as generators have varying performance levels, and there are indeed generators that make no progress.
      Therefore, instead of assigning all FITS files to generators initially, scheduling is done dynamically.
      For details, see [here](./dynamic-dispatch.md).
    
    * Generators tile the FITS files assigned to them
      * After this phase is complete, users can display a preview
        * However, there is no need to use `/dev/shm` or similar; simply save to `emptyDir` (writes to this location should be very fast due to kernel buffering)

* MergeSingleFitsTiles Phase
  * Coordinator instructs generators to merge tiles
    * The coordinator is aware of which generators hold which tiles.
  * A single tile may be generated from multiple FITS files, and these are exchanged between generators for merging
  * After merging is complete, SingleFitsTiles are deleted

* TransferPackedTiles Phase
  * Coordinator instructs generators to compress and upload
    * If each tile is one object, the number of objects becomes too large, so approximately 4x4 tiles are grouped into a single object
    * The grouped objects are uploaded to object storage
  * After uploading is complete, PackedTiles are deleted

## State Management

* This application runs on Kubernetes, so it is assumed that each component (particularly generators) will frequently restart due to memory pressure and other issues.
* Global state of the entire application that needs to be persisted is stored in the database; everything else is maintained in the coordinator's memory.

### Memory in Coordinator

* Jobs being processed
* Processing requests

### Database

The database stores information necessary for the coordinator to delete incomplete data when it terminates abnormally.


## Request Queue

* When a user opens a page, a request for that visit enters the request queue
* Request entries have the following information:
    ```python
    @dataclass
    class RequestEntry:
        visit: VisitName
        vote: int
        first_request: datetime
    ```
* Processing slots are allocated in order of largest `vote` and then earliest `first_request` when slots become available.
  * That is, items with more votes, and among those with the same number of votes, those submitted first are processed in order.
  * The vote count increases by 1 when a page is opened and decreases by 1 when a user leaves the page.
* A semaphore can be used to limit concurrent execution during tile creation
  * Preview becomes possible
* `When the user`


### Implementation

When a processing slot becomes available, the highest priority item from the request queue is pushed.
There are 2 processing slots, and simultaneously
