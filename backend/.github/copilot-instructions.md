# Copilot Instructions for FOV-Quicklook Backend

## Architecture Overview

Read `/docs/concept.ja.md` for system design and terminology.

**Purpose**: Rapid tile-based visualization of LSST Camera imagery (189 FITS files/shot, ~12GB total).

**Key Components** (TCP-communicating processes):
- **Coordinator** (`src/quicklook/coordinator/`): Single orchestrator issuing tile generation jobs via RPC
- **Generator** (`src/quicklook/generator/`): Multiple workers processing tiles (k8s pods, variable performance)
- **Database**: Persistent state for tiles (in-progress, completed)
- **Frontend**: User-facing tile retrieval and composition

**Tile Generation Pipeline** (`quicklook` = `(exposure, dataType)` unit):
1. **GenerateSingleFitsTiles**: Dynamic FITS→tile conversion (enables preview)
2. **MergeSingleFitsTiles**: Cross-generator tile merging
3. **TransferPackedTiles**: 4×4 tile packing → S3 upload

**Critical Design Patterns**:
- **Dynamic Dispatch** (`src/quicklook/utils/adaptive_map/`): Adaptive work distribution to compensate for variable pod performance. See `README.ja.md` for algorithm.
- **RPC Communication** (`src/quicklook/comm/`): Coordinator→Generator via pickled function calls over HTTP streaming
  - Generators register with Coordinator via periodic heartbeats
  - Coordinator tracks generator availability and capacity
  - Example: `Rpc.create(generate_single_fits_tiles, job, ccd_refs)`
- **Pipeline Stages** (`src/quicklook/utils/pipeline/`): Concurrent multi-stage processing with configurable parallelism (see `config.pipeline_*`)

## Python Development

**Environment**:
- Python 3.13 in `./.venv`
- Always use `./.venv/bin/{python,pip,pytest}` explicitly

**Code Style**:
- Use modern type hints: `list[int]` not `List[int]`, `int | None` not `Optional[int]`
- Avoid trivial comments (self-evident from names); write higher-abstraction explanations
- Example from `src/quicklook/types.py`: `VisitName` is a string subclass with `.data_type` and `.name` properties

**Testing** (`pytest.ini` configured):
- Write `def test_*` functions (not `class Test*`)
- Co-locate: `src/quicklook/job/__init__.py` → `src/quicklook/job/test_job.py`
- Async tests auto-detected (no `@pytest.mark.asyncio` needed unless overriding)
- Mark slow tests: `@pytest.mark.slow` (excluded by default via `-m "not slow"`)
- Run all tests: `make test/all` or `./.venv/bin/pytest -m "not slow or slow"`
- Timeout guards for deadlock risks

**Dependencies**:
- SQLAlchemy 2.0+ (use new `select()` API)
- FastAPI + uvicorn (coordinator/generator apps)
- Custom lib: `mineo-fits-decompress` (local package in `lib/`)

## Key Workflows

**Run Tests**:
```bash
make test              # Fast tests only
make test/all         # Include slow tests
make test/cov-server  # View coverage at localhost:4000
```

**Type Checking**:
```bash
make pyright        # One-shot type check
make pyright/watch  # Watch mode
```

**Configuration** (`src/quicklook/config/`):
- `Config` class with `pydantic-settings`
- Prefix: `QUICKLOOK_*`, nested delimiter: `__`
- Test environment: `pytest.ini` sets `QUICKLOOK_environment=test` and S3 configs

**Data Sources** (`src/quicklook/datasource/`):
- Abstract: `DataSourceBase` with `query_visits()`, `list_ccds()`, `get_data()`, `get_metadata()`
- Implementations: `butler` (production), `dummy` (testing)
- Get instance: `from quicklook.datasource import get_datasource`

## Domain-Specific Concepts

**Visit & CCD References**:
- `VisitName`: String with format `<parts>:<data_type>:<name>` (e.g., `exp123:raw:visit001`)
- `CcdDataRef`: `(visit, ccd)` tuple uniquely identifying FITS data
- `TilePos`: `(level, i, j)` where level 0 = finest, increasing level doubles tile size

**Object Storage** (`src/quicklook/object_storage/`):
- PackedTiles (4×4 groups) stored as `pickle` lists in S3
- Keys: `quicklooks/{visit}/packed-tile/{level}/{i}/{j}.npy.zstd.list.pickle`
- LRU cache on `get_packed_tile_array()` (tiles ~100-200KB, packed ~1.6-3.2MB)

**Job Management** (`src/quicklook/job/`):
- `Job`: Unit of work in pipeline
- Local storage: `config.job_local_dir` for intermediate tiles
- Generator capacity: `config.generator_max_concurrent_jobs`

## Internationalization

- `*.ja.md`: Japanese documentation
- When asked to translate, generate corresponding `*.md` in English (overwrite if exists)

## Common Pitfalls

- Don't assume uniform generator performance → use `adaptive_map` for distribution
- RPC functions must be importable on both coordinator and generator sides
- Generators can restart (k8s OOM) → state in database, not generator memory
- Test with `config.data_source=dummy` to avoid Butler dependencies
