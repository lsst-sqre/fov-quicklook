# Communication between Coordinator and Generator

The Coordinator issues RPC calls to Generators to request job execution.
(Generators are what this application specifically calls them; in general terms, they perform the role of Workers.)
The Coordinator needs to maintain a list of available Generators before issuing RPCs.
We design a mechanism to ensure communication from Coordinator to Generator based on the following assumptions.

* Only one Coordinator exists in the entire system.
* Multiple Generators exist in the entire system, and the Coordinator uses them (via `dynamic_dispatch` etc.).
* Both Coordinator and Generator may terminate unexpectedly. (due to running on Kubernetes)

## Implementation

* Both Generator and Coordinator are implemented as FastAPI applications.
* Generator
  * Periodically (including at startup) notifies the Coordinator of its existence.
    * Notifies the following:
      * Port number for RPC reception of its own process
      * Number of jobs that can be processed simultaneously
    * If communication fails:
      * The Coordinator has stopped or a network failure has occurred.
      * Terminate its own process. (Restart is left to Kubernetes)
* Coordinator
  * Receives notifications from Generators.
  * Registers the Generator as an available Generator.
  * Periodically checks connectivity to registered Generators.
    * If connectivity check fails, the Generator is considered unavailable.
    * Removes the Generator from the list of available Generators.

* Connectivity checks do not retry
  * Actively restart if an unstable state occurs

## Module Interface

### Generator

```python
from quicklook.comm import coordinator

app = FastAPI(lifespan=coordinator.lifespan)
app.include_router(coordinator.router)

# Submit jobs to all generators from user requests
@app.get('/available_generators')
async def available_generators():
    return coordinator.get_available_generators()
```

### Coordinator

```python
from quicklook.comm import generator

app = FastAPI(lifespan=generator.lifespan)
app.include_router(generator.router)
```

Used in such a form.

* Create necessary endpoints with `coordinator.router`
  * `/healthz`
    * Connectivity check from Generator
  * `/register`
    * Registration from Generator
* Create necessary endpoints with `generator.router`
  * `/healthz`
    * Connectivity check from Coordinator
  * `/rpc`
    * Accept RPC calls from Coordinator
