# Route List

This is a list of available routes in this application.

## Main Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | Navigate → `/visits` | Root path automatically redirects to `/visits` |
| `/visits` | Home | Visits list page (main page). Automatically redirects to the latest available visit |
| `/visits/:visitId` | Home | Page for a specific visit ID |
| `/header/:visitId/:ccdName` | FItsHeaderPage | FITS header information display page |
| `/config` | ConfigPage | Configuration page for ContextMenu templates and other settings |

<!-- ## Admin Routes (planned to be hidden in the future)

| Path | Component | Description |
|------|-----------|-------------|
| `/admin/pod_status` | PodsStatus | Pod status management page |
| `/admin/jobs` | Jobs | Job management page |
| `/admin/cache-entries` | CacheEntries | Cache entries management page |
| `/admin/storage` | StorageExplorer | Storage explorer | -->

## Query Parameters

### detectors Parameter

Query parameter for specifying CCD detectors to highlight.

- **Format**: `?detectors=detector1,detector2,detector3`
- **Value**: Comma-separated detector names or IDs
- **Example**: `?detectors=R01_S00,R01_S01` or `?detectors=1,2,3`
- **Behavior**: 
  - For numeric values only, uses internal ccdNameTable to convert to detector names
  - For string values, uses them directly as detector names
