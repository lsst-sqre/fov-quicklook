# 🌀 AsyncProcessGenerator — Asynchronous Streaming of Heavy Processing in Separate Process

A utility using a **process pool** to **execute generator functions with CPU-bound heavy processing or blocking I/O in separate processes while retrieving results sequentially as an `async generator`**.

## ✨ Features

- **Efficient execution with process pool**  
  → Reuse existing worker processes instead of creating new ones each call  
- **Execution in separate process**  
  → Doesn't block event loop or other requests  
- **Real-time streaming**  
  → Sequentially receive `yield` values as async generator  
- **Error propagation**  
  → Exceptions raised in the process are re-raised on the caller side  
- **Automatic cleanup**  
  → Process termination handled automatically  
- **FastAPI / StreamingResponse support**  
  → Can be used directly for sequential response generation in Web APIs  
- **Initializer function support**  
  → Execute initialization processing when worker processes start  

## 📝 Usage

### Basic Usage

```python
import asyncio
from quicklook.utils.async_process_generator import create_async_process_pool

def heavy_generator(count: int):
    """Example of a generator function with heavy processing"""
    import time
    for i in range(count):
        # Simulate heavy processing
        time.sleep(1)
        yield f"Processing complete: {i + 1}/{count}"

async def main():
    # Create process pool
    async with create_async_process_pool(max_workers=4) as pool:
        async for result in pool.run_async_process_generator(heavy_generator, 5):
            print(f"Received: {result}")

# Execute
asyncio.run(main())
```

### Usage with FastAPI lifespan

Manage process pool in FastAPI application's lifespan and use it in request handlers.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from quicklook.utils.async_process_generator import create_async_process_pool

# Global process pool
_process_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _process_pool
    # Initialize process pool
    async with create_async_process_pool(max_workers=4) as pool:
        _process_pool = pool
        try:
            yield
        finally:
            _process_pool = None

app = FastAPI(lifespan=lifespan)

def heavy_data_processing(data_size: int):
    """Generator for heavy data processing"""
    import time
    for i in range(data_size):
        # CPU-intensive processing
        time.sleep(0.5)  # Simulate heavy processing
        yield f"Data {i+1} processing complete\n"

@app.get("/stream/{count}")
async def stream_heavy_process(count: int):
    if _process_pool is None:
        raise RuntimeError("Process pool not initialized")
    
    return StreamingResponse(
        _process_pool.run_async_process_generator(heavy_data_processing, count),
        media_type="text/plain"
    )
```

### Using Initializer Functions

Execute initialization processing when worker processes start.

```python
from quicklook.utils.async_process_generator import create_async_process_pool

# Global variable (independent for each worker process)
_db_connection = None

def initialize_worker():
    """Worker process initialization"""
    global _db_connection
    _db_connection = connect_to_database()
    print(f"Worker initialized with DB connection")

def query_generator(query: str):
    """Generator that executes DB query"""
    global _db_connection
    cursor = _db_connection.execute(query)
    for row in cursor:
        yield row

async def main():
    # Create process pool specifying initializer function
    async with create_async_process_pool(
        max_workers=4,
        initializers=[initialize_worker]
    ) as pool:
        async for row in pool.run_async_process_generator(query_generator, "SELECT * FROM users"):
            print(row)
```

## 🔧 Parameters

### `create_async_process_pool`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_workers` | `int \| None` | `None` | Number of worker processes in pool (None means CPU count) |
| `initializers` | `list[Callable[[], None]] \| None` | `None` | List of initializer functions to execute in each worker process |

### `pool.run_async_process_generator`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `generator_func` | `Callable` | - | Synchronous generator function to execute |
| `*args` | `Any` | - | Positional arguments passed to generator function |
| `**kwargs` | `Any` | - | Keyword arguments passed to generator function |

## 📦 Use Cases

- **Large file processing**  
  Execute sequential read/write and transformation without blocking main process

- **CPU-bound computation**  
  Sequential generation results from machine learning models, image processing, numerical computation, etc.

- **Streaming responses**  
  Server-Sent Events (SSE) or FastAPI `StreamingResponse` with sequential responses

- **Progress display for long-running processing**  
  Send batch processing progress to frontend in real-time

## ⚠️ Cautions

- **Inter-process communication overhead**  
  When yielding small data frequently, thread pool (`anyio.to_thread`) may be more efficient

- **Pickle-able objects**  
  Values yielded must be pickle-able (standard Python types are fine)

- **Memory usage**  
  Buffering in Queue, so be careful when yielding large amounts of data at once

## 🔄 Migration Guide (from old API)

If you were using the previous `run_async_process_generator` function directly, rewrite as follows:

**Old code:**
```python
async for item in run_async_process_generator(my_generator, arg1, arg2):
    process(item)
```

**New code:**
```python
async with create_async_process_pool() as pool:
    async for item in pool.run_async_process_generator(my_generator, arg1, arg2):
        process(item)
```

For FastAPI applications, managing process pool in lifespan is recommended (see example above).

## 🚀 Summary

With `create_async_process_pool`, you can separate **"asynchronous FastAPI apps" + "synchronous heavy processing"** well and create a scalable structure.

Through the process pool, reduce the overhead of creating processes with each call, and stream results of heavy processing in real-time without blocking the main process's event loop. It's a powerful utility.
