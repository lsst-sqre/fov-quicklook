# GenerateSingleFitsTiles Coordinator

## Overview

This module performs cooperative processing to dynamically allocate CCD processing to multiple generators (Generator Pods) and generate tiles from FITS data.

## Main Design Philosophy

### Dynamic Workload Balancing

Generator performance is not uniform:
- Runs as a Kubernetes Pod, performance varies based on node load
- Some generators may become extremely slow
- Static pre-allocation creates bottlenecks

To address this problem, we adopt a **two-phase dynamic allocation strategy**.

## Two-Phase Processing Algorithm

### Phase 1: Initial Dispatch

Submit all CCDs to each generator once.

```
remaining_ccds = [ccd1, ccd2, ..., ccdN]
↓
Submit sequentially as capacity becomes available in each generator
```

**Characteristics**:
- Each generator processes `config.generator_max_concurrent_ccds_per_job` CCDs simultaneously
- Submit multiple CCDs in initial batch (cold start countermeasure)
- Faster generators process more CCDs

### Phase 2: Resubmission (Resubmit)

After all CCDs have been submitted once, continue resubmitting incomplete CCDs.

```
while incomplete CCDs exist:
    Get the oldest unfinished CCD that was submitted
    ↓
    Resubmit to generator with available capacity
    ↓
    Faster generator takes over processing
```

**Benefits**:
- CCDs being processed by slow generators can be processed in parallel by fast generators
- Adopt first-completed metadata (no problem even with duplicate execution)
- Extremely slow generators don't become bottlenecks

**Example**:
```
Generator A: Processing speed 10 ccd/min
Generator B: Processing speed 1 ccd/min (extremely slow)

After Phase 1:
- Generator A: ccd1, ccd2, ... ccd100 → all complete
- Generator B: ccd101 → still processing (50 more minutes)

Phase 2:
- Generator A: Resubmit ccd101 when capacity becomes available
- Generator A: Complete ccd101 in 1 minute ✓
- Generator B: Still processing ccd101, but result is ignored
```

## Data Structures

### State Management

```python
remaining_ccds: deque[CcdDataRef]
    # Used in Phase 1. CCDs never submitted yet

submitted_ccds: list[CcdDataRef]
    # Maintains submit order. Used to search for incomplete CCDs in Phase 2

phase2_index: int
    # Round-robin index for Phase 2

ccd_metadata_dict: dict[CcdName, CcdMetadata]
    # Metadata of completed CCDs. Store only first-completed

ccd_generator_map: dict[CcdName, GeneratorId]
    # Records which generator completed first
```

### Processing Flow

```python
async def get_next_ccd_to_submit() -> CcdDataRef | None:
    # Phase 1: Get from remaining_ccds
    if remaining_ccds:
        ccd_ref = remaining_ccds.popleft()
        submitted_ccds.append(ccd_ref)
        return ccd_ref
    
    # Phase 2: Get incomplete CCDs in round-robin order
    for offset in range(len(submitted_ccds)):
        idx = (phase2_index + offset) % len(submitted_ccds)
        ccd_ref = submitted_ccds[idx]
        if ccd_ref.ccd_name not in ccd_metadata_dict:
            phase2_index = (idx + 1) % len(submitted_ccds)
            return ccd_ref
    
    # All complete
    return None
```

**Important**: In Phase 2, the same CCD is **allowed** to be processed simultaneously by multiple generators. Round-robin resubmits incomplete CCDs repeatedly, allowing fast generators to process more aggressively.

## Termination Condition

When metadata for all CCDs is obtained, send termination signal (`None`) to each worker.

```python
async def should_send_termination_signal() -> bool:
    all_completed = len(ccd_metadata_dict) == len(ccd_refs)
    if all_completed and workers_notified < len(generator_list):
        workers_notified += 1
        return True
    return False
```

**Important**: 
- Each worker has an independent RPC stream, so each needs a termination signal
- `workers_notified` counter prevents duplicate sends

## Concurrent Processing Synchronization

All state changes are protected by `asyncio.Lock`:

```python
lock = asyncio.Lock()

async with lock:
    # Read and modify state
    if remaining_ccds:
        ccd_ref = remaining_ccds.popleft()
        submitted_ccds.append(ccd_ref)
```

This prevents conflicts even when multiple workers modify state simultaneously.

## Configuration Parameters

- `config.generator_max_concurrent_ccds_per_job`: Number of CCDs each generator can process concurrently (default: as configured)

## Performance Characteristics

### Worst Case Improvement

**Traditional Implementation (Phase 1 only)**:
```
Total processing time = max(processing time for each generator)
```
A single extremely slow generator becomes the bottleneck.

**Two-Phase Implementation (Phase 1 + Phase 2)**:
```
Total processing time ≈ Total CCDs / Total throughput of fast generators
```
Minimize impact of slow generators.

### Trade-offs

**Advantages**:
- Eliminate slow generator bottleneck
- Significantly reduce total processing time
- Automatic optimal load distribution

**Costs**:
- Some CCDs are processed redundantly (computational resource waste)
- Metadata uses only first-completed result (subsequent results discarded)

In production environments, extremely slow generators (such as high-load Kubernetes nodes) do exist, and this redundant processing cost is well justified.

## Related Modules

- `quicklook.rpc.queue.RpcQueue`: Queue mechanism for dynamic CCD supply
- `quicklook.generator.generate_single_fits_tiles`: Generator-side processing implementation
- `quicklook.comm.coordinator.get_available_generators`: Obtaining available generators
