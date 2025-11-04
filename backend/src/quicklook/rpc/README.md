# RPC

## Overview

In this application, there are scenarios where nodes cooperate to perform processing.
Communication is done through HTTP and WebSocket, but writing communication processing for all cooperative processing scenarios is cumbersome.

For this reason, we want to abstract communication processing to make cooperative processing code concise.
This benefit also improves testability by eliminating communication processing from the called-side function.

The simplest case is:

```python
def f(arg1, arg2):
    ...

result = await Rpc(f, arg1, arg2).run()
```

This calls a synchronous function on another node and receives the result asynchronously.
The function executed on the other node must be synchronous.
(An error is raised if the function is asynchronous at runtime)

When the target function is a generator:

```python
def f():
    for i in range(5):
        yield i

async for j in Rpc(f).run():
    print(j)
```

this is also possible.

Finally, another case we want to support is when the caller's input is a queue.

```python
import asyncio
import queue
from quicklook.rpc import Rpc, RpcQueue

# Sentinel value for queue termination (defined on application side)
QUEUE_END = object()

client_queue = asyncio.Queue()

def f(q: queue.Queue):
    while True:
        item = q.get()
        if item is QUEUE_END:
            break
        yield item

async def produce():
    for i in range(5):
        await client_queue.put(i)
    await client_queue.put(QUEUE_END)

task = asyncio.create_task(produce())

async for i in Rpc(rpc_endpoint_url, f, RpcQueue(client_queue)).run():
    print(i)
```

Note: Queue termination handling should be managed on the application side, not by the RPC module.
In the above example, a sentinel value `QUEUE_END` is used to signal queue termination.

The above code is for client-side usage.

On the server side, RPC endpoints are defined as follows:

```python
from fastapi import FastAPI, WebSocket

app = FastAPI(lifespan=rpc_lifespan)

@app.post("/rpc")
async def rpc_endpoint(ws: WebSocket):
    return await create_rpc_endpoint(ws)
```

Implement related classes and functions such as `Rpc`, `RpcQueue`, `rpc_endpoint`, and `create_rpc_endpoint`.

## Implementation Requirements

* There is already code named `rpc` in the codebase, but implement this as a completely independent new module.
* Place necessary files in this directory.
* Server side (the side being called by RPC) receives RPC requests via FastAPI.
    * Communication between server and client uses WebSocket (from the `websockets` module).
    * Send and receive pickled objects over WebSocket.
* Only synchronous functions are executed on the server side
* Results are received asynchronously on the client side.
* On the server side, use process pool to execute each RPC call in a separate process.
    * Implement a FastAPI `lifespan` `contextmanager` for this.
* Actively use type hints.
    * Use `ParamSpec` and `@overload`.
* Communication uses several types of messages, and use Python's `match` statement actively for branching between those types.
* Decompose necessary functionality and design it to work independently, with individual tests for each.
* Perform `git commit` in small units.
* If an error occurs on the server side, raise an `RpcRemoteError` exception on the client side.
* `RpcQueue` receives `asyncio.Queue` and returns `queue.Queue` as a type.
    * In reality, when an `RpcQueue` instance is sent remotely, it receives special handling and operates as a queue connecting nodes.
* Development Notes
    * Use the Python environment in `./.venv`.
    * When using shell features, assume `fish` shell works.
    * Testing
        * This type of module can deadlock. Specify a timeout in tests.
            * Usage like `timeout 10 ./.venv/bin/pytest ...` is recommended.
        * Aim for 100% test coverage. Branches that only raise exceptions don't need to be covered (use `#pragma: no branch` for such branches).

## Implementation Details

* There are 5 types of messages between client and server: Call, ResponseType, Return, Error, Exit, and Yield.
* ResponseType returns whether the function called on the server is a generator.
* Starts with a Call from client and ends with Exit from server.
* After receiving Return or Error, client keeps the connection open until Exit arrives.
