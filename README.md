# FOV-Quicklook: Distributed Tile-based Visualization System for LSST Camera Images

FOV-Quicklook is a high-performance distributed system for rapidly visualizing LSST camera image data. It enables interactive browsing of massive astronomical datasets by converting FITS files into an efficient tiled format that can be rendered at any zoom level within seconds.

## Overview

### The Challenge

Each LSST observation produces 189 FITS files totaling approximately 12 GB of compressed data. Traditional approaches that load entire datasets into memory are impractical. FOV-Quicklook solves this by:

- **Distributing** tile generation across multiple worker pods
- **Streaming** tile data to frontend clients on-demand

### System Architecture

```
[User Browser]
    ↓
[Frontend (React + TypeScript, multiple Pods)]
    ↓
[Coordinator (single Pod) - Orchestrator & RPC Hub]
    ↓
[Generators (multiple Pods, ~9 in production)]
    ├→ Fetch FITS from Butler data source
    ├→ Generate tiles (local temporary storage)
    └→ Merge and upload to S3/MinIO
    
[PostgreSQL Database] - Persistent job state for recovery
[S3/MinIO Storage] - Packed tile cache (~1.6-3.2 MB per 4×4 group)
```

## Key Components

### Coordinator
- **Role**: Orchestrates the entire tile generation pipeline
- **Responsibilities**:
  - Receives requests from frontend users
  - Discovers and monitors generator pods via heartbeat mechanism
  - Dynamically dispatches FITS files to generators
  - Coordinates tile merging across multiple generators
  - Manages job state and recovery in PostgreSQL
- **Deployment**: Single pod in production

### Generator
- **Role**: Executes tile generation and image processing tasks
- **Responsibilities**:
  - Receives tasks from coordinator via HTTP RPC
  - Generates tiles from raw FITS files
  - Merges tiles across CCD boundaries
  - Compresses and uploads tile groups to S3/MinIO
  - Reports progress via streaming JSON responses
- **Deployment**: Multiple pods in production (~8 typically)

### Frontend
- **Role**: Provides user interface and REST API for tile access
- **Responsibilities**:
  - Serves the interactive Quicklook viewer (React + StellarGlobe 3D component)
  - Handles user requests and manages UI state
  - Retrieves tiles from cache (S3/MinIO)
- **Deployment**: Multiple pods for horizontal scaling

### Database
- **Purpose**: Persistent cache state store
- **Technology**: PostgreSQL with SQLAlchemy ORM
- **Stored Data**:
  - Quicklook job metadata (visit, data type, status)
- **Recovery**: Allows coordinator to clean up incomplete jobs after restarts

## Three-Stage Tile Generation Pipeline

### Stage 1: GenerateSingleFitsTiles
- Converts raw FITS files into individual tiles
- Each FITS file is processed by a single generator
- Output: Individual `.npy` files stored locally
- Preview functionality will be available after this stage.

### Stage 2: MergeSingleFitsTiles
- Merges tiles that span multiple FITS files (CCD boundaries)
- Generators coordinate via RPC to exchange tile data
- Consolidates temporary tile files

### Stage 3: TransferPackedTiles
- Groups 4×4 tiles into a single packed object (~1.6-3.2 MB each)
- Compresses packed tiles using Zstandard compression
- Uploads to S3-compatible object storage
- Cleans up temporary files
- **Final**: Tiles available for efficient client-side rendering

## Project Structure

```
backend/                         # Python 3.13 FastAPI backend
  src/quicklook/
    coordinator/                 # RPC hub, job orchestration, heartbeat management
      api/                       # REST endpoints and admin interface
      quicklookjob/              # Job state and task definitions
    generator/                   # Tile generation and merging
      api/                       # RPC handlers for tasks
    frontend/                    # Web API for UI (REST + WebSocket)
    datasource/                  # Data abstraction layer (Butler or dummy)
    db/                          # SQLAlchemy models (PostgreSQL)
    rpc/                         # HTTP streaming RPC layer
    utils/
      pipeline/                  # Configurable multi-stage pipeline
    types.py                     # Core type definitions
    config/__init__.py           # Pydantic configuration (env: QUICKLOOK_*)
  tests/
    integration_tests/           # Full system tests with auto-launched components
    coordinator/                 # Unit tests for coordinator logic
    generator/                   # Unit tests for generator logic
  pytest.ini                     # Test configuration

frontend/app/                    # React + TypeScript + Vite
  src/
    pages/                       # Quicklook viewer, admin panel
    store/api/                   # RTK Query hooks (auto-generated from OpenAPI)
    StellarGlobe/                # 3D spherical viewer component
  public/                        # Static assets

k8s/                             # Kubernetes deployment
  phalanx/                       # Helm charts for integration
    applications/fov-quicklook/

docs/
  concept.md                     # System design and terminology
  dev.md                         # Development environment setup
  request.md                     # HTTP API request examples
  tasks.md                       # Task definitions
 
notes/ 
  requirements.md                # Pod replicas, resource limits, cache settings
  templating.md                  # Helm template notes
```

## Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL 13+
- S3-compatible object storage (MinIO or AWS S3)
- Kubernetes cluster (microk8s for development)

### Backend Setup

```bash
cd backend
python3.13 -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/pip install -e '.[dev]'
```

### Frontend Setup

```bash
cd frontend/app
npm install
```

### Development on microk8s

Run the interactive dev environment on the microk8s node that has this checkout mounted:

```bash
git submodule update --init --recursive
sh dev/microk8s-dev/run.sh all
sh dev/microk8s-dev/run.sh status
```

Attach to the tmux sessions inside the dev pods:

```bash
kubectl -n fov-quicklook-dev exec -it deploy/backend-dev -- tmux a
kubectl -n fov-quicklook-dev exec -it deploy/frontend-dev -- tmux a
```

Access the UI through port-forwarding:

```bash
kubectl -n fov-quicklook-dev port-forward svc/frontend-dev 5173:5173
```

Then open `http://127.0.0.1:5173/fov-quicklook-dev/`.

### Running Tests

```bash
cd backend
make test              # Fast tests only (default: skip @pytest.mark.slow)
make test/all          # Include slow tests
make test/cov-server   # View coverage HTML at localhost:4000
```

### Type Checking

```bash
cd backend
make pyright           # One-time check
make pyright/watch     # Continuous monitoring
```

### Deployment

Branch images are built by GitHub Actions on push.
ArgoCD / broker deployment workflow is documented in `/dev-docs/phalanx.ja.md`.

## Configuration

All configuration uses environment variables with the `QUICKLOOK_` prefix:

### Key Configuration Variables

```bash
# Data source
QUICKLOOK_data_source=butler|dummy     # Data source type (default: butler)

# Storage
QUICKLOOK_s3_tile__access_key=<key>
QUICKLOOK_s3_tile__secret_key=<secret>
QUICKLOOK_s3_tile__endpoint=http://minio:9000
QUICKLOOK_s3_tile__bucket=fov-quicklook-tiles

# Timeouts
QUICKLOOK_generate_timeout=300         # seconds
QUICKLOOK_merge_timeout=300
QUICKLOOK_transfer_timeout=300

# Coordinator
QUICKLOOK_coordinator_port=9501
QUICKLOOK_heartbeat_interval=30        # seconds

# Local paths
QUICKLOOK_job_local_dir=/tmp/quicklook

# Admin
QUICKLOOK_admin_page=true|false
```

See `backend/src/quicklook/config/__init__.py` for complete configuration options.

## RPC Communication Protocol

The coordinator communicates with generators using HTTP streaming RPC:

**1. Generator Discovery**:
- Each generator periodically sends `POST /register_generator` with `{host, port}`
- Coordinator maintains in-memory registry
- Periodic health checks via `GET /healthz`
- Unresponsive generators are automatically pruned

**2. Task Dispatch (Synchronous HTTP Streaming)**:
- Coordinator: `POST http://{generator}:{port}/quicklooks` with `GenerateTask` payload
- Generator: Streams JSON progress messages, then final result
- Client parses streamed objects using `message_from_async_reader()` utility

**3. Task Types** (defined in `backend/src/quicklook/coordinator/quicklookjob/tasks.py`):
- `GenerateTask`: FITS files to tile and generator assignment
- `MergeTask`: Tiles to merge with producer tracking
- `TransferTask`: Packed tiles to compress and upload

## Performance Characteristics

- **Tile Size**: ~100-200 KB per individual tile
- **Packed Tile Size**: ~1.6-3.2 MB per 4×4 group (after compression)
- **Generation Time**: ~100-200 tiles/second per generator pod
- **Time to Preview**: ~5-10 seconds from request to basic tile availability
- **Time to Full Cache**: ~30-60 seconds depending on cluster size

## Development Workflow

### Updating Frontend Styles

After modifying SCSS:
```bash
cd frontend/app
npm run scss-types  # Regenerate style type definitions
```

### Debugging Failed Tests

```bash
cd backend
make test -- -vv -k test_name  # Verbose output
make test -- -s                # Show print statements
```

## Documentation

- **Architecture**: `/dev-docs/architecture.ja.md` - System structure, data flow, runtime assumptions
- **Development Setup**: `/dev-docs/dev.ja.md` - microk8s-based development workflow
- **Backend Details**: `/dev-docs/backend.ja.md` - Python patterns, testing, configuration
- **Frontend Details**: `/dev-docs/frontend.ja.md` - SCSS build, RTK Query, test workflow
- **CI / Review App**: `/dev-docs/ci.ja.md` - review app pipeline and shared fixtures
- **Butler/Data Query Guide**: `/dev-docs/features/butler-data-query.ja.md` - How Data Query maps onto Butler queries, dimensions, and datasets
- **Deployment**: `/dev-docs/phalanx.ja.md` - ArgoCD / Phalanx deployment workflow
- **Routes Note**: `/docs/routes.md` - Route inventory
- **Templating Note**: `/docs/templating.md` - Template-related memo

## Code Style Guidelines

### Python
- Type hints are mandatory: use `list[int]` (not `List[int]`), `int | None` (not `Optional[int]`)
- Comments explain **why**, not **what** - let code be self-documenting
- Python 3.13+ features are acceptable

### TypeScript/React
- Use strict type checking (minimize `any` usage)
- Prefer functional components with hooks
- Props must be properly typed interfaces

### Configuration
- Use environment variables with `QUICKLOOK_` prefix
- Nested config uses `__` separator (e.g., `QUICKLOOK_s3_tile__access_key`)
