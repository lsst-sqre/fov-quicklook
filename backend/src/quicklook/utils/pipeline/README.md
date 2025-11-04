## Coordinator's Pipeline Execution Model

The `quicklook.utils.pipeline` module provides a lightweight pipeline implementation for writing stage processing connected by asynchronous queues.

### Stage

* `Stage.process`
	* Asynchronously processes one input and returns the value to pass to the next stage.
	* If `Skip` exception is raised, that item is not passed to subsequent stages and `on_finish`.
* `parallel`
	* Limits the number of workers running the same stage simultaneously.
	* Tests verify that maximum concurrent execution does not exceed the configured value.
* `item_picker`
	* Can customize which item to retrieve from the input buffer.
	* For example, strategies like selecting high-priority jobs with `max` are possible, and tests confirm latest-item-first behavior.
* `on_enter` / `on_exit`
	* Can insert auxiliary processing before and after processing each item. Used for monitoring and resource acquisition.

### Pipeline

* `Pipeline.append`
	* Adds stages in series, updating input/output types according to type parameters.
* `Pipeline.on_finish`
	* Receives output from the final stage and performs post-completion processing asynchronously.
	* Since it is awaited internally, the pipeline doesn't process the next completion notification until the async processing here completes.
* `Pipeline.run`
	* Launches worker groups as a context manager and provides a handle with `push`/`cancel`.
	* Cancels all tasks and cleans up when the context exits.

### Test Coverage Points

* Basic processing flow through serial stages
* Call order of `on_enter`/`on_exit` hooks
* Skip behavior with `Skip` exception
* Maximum concurrent execution limit with `parallel` specification
* Priority control via `item_picker`
