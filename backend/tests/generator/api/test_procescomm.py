import time
import multiprocessing

from quicklook.generator.api.processcomm import Connection, spawn_process_with_comm


def sample_target(child_comm: Connection) -> None:
    message = child_comm.recv()
    if message == "ping":
        child_comm.send("pong")


def test_spawn_process_with_comm() -> None:
    with spawn_process_with_comm(sample_target) as handle:
        handle.comm.send("ping")
        response = handle.comm.recv()
        assert response == "pong"


def sigint_target(child_comm: Connection) -> None:
    # Notify the parent process that preparation is complete
    child_comm.send("ready")

    # Run continuously in an infinite loop (should be terminated by SIGINT)
    while True:
        time.sleep(0.1)


def test_process_handle_sigint() -> None:
    with spawn_process_with_comm(sigint_target) as handle:
        # Wait for the child process to be ready
        response = handle.comm.recv()
        assert response == "ready"

        # Verify that the process is running
        assert handle.process.is_alive()

        # Send SIGINT signal
        handle.sigint()

        # Verify that the process has terminated
        assert not handle.process.is_alive()


def pool_worker(x: int) -> int:
    """Sample worker function - simply doubles the value and returns it"""
    time.sleep(0.1)  # Assume it takes some processing time
    return x * 2


def pool_target(child_comm: Connection) -> None:
    """Target function using multiprocessing.Pool"""
    # Create a Pool
    with multiprocessing.Pool(processes=4) as pool:
        # Notify the parent process that preparation is complete
        child_comm.send("pool_ready")

        # Submit long-running tasks to the Pool
        # Normally, map_async or apply_async would be used, but here we create
        # an endless loop for testing termination with SIGINT
        try:
            # Simulate a scenario with a large number of tasks
            result_iter = pool.imap_unordered(pool_worker, range(1000))

            # Process results gradually
            for _ in result_iter:
                # Normally, results would be processed here, but for testing, we pass
                time.sleep(0.05)
        except KeyboardInterrupt:
            # This block is executed when SIGINT is sent
            child_comm.send("sigint_received")
            # Clean up properly and exit
            return


def test_process_with_pool_sigint() -> None:
    """Test to verify that sending SIGINT while using Pool in child process terminates properly"""
    with spawn_process_with_comm(pool_target) as handle:
        # Wait for the child process to complete Pool preparation
        response = handle.comm.recv()
        assert response == "pool_ready"

        # Verify that the process is running
        assert handle.process.is_alive()

        # Wait a bit before sending SIGINT (to ensure Pool has started processing)
        time.sleep(0.5)
        handle.sigint()

        # Wait a bit for the process to terminate properly
        timeout = time.time() + 5.0  # 5 second timeout
        while handle.process.is_alive() and time.time() < timeout:
            time.sleep(0.1)

        # Verify that the process has terminated
        assert not handle.process.is_alive()


def error_target(child_comm: Connection) -> None:
    """Function for child process that intentionally raises an error"""
    # Notify the parent process that preparation is complete
    child_comm.send("ready_for_error")

    # Intentionally raise an error
    raise RuntimeError("This is an intentional error for testing")


def test_child_process_error_isolation() -> None:
    """Test to verify that errors in child process don't affect the parent process"""
    with spawn_process_with_comm(error_target) as handle:
        # Wait for the child process to be ready
        response = handle.comm.recv()
        assert response == "ready_for_error"

        # The child process should raise an error here
        # Wait a bit for the process to terminate
        timeout = time.time() + 5.0  # 5 second timeout
        while handle.process.is_alive() and time.time() < timeout:
            time.sleep(0.1)

        # The process should have terminated with an error
        assert not handle.process.is_alive()

        # Verify that the exit code is non-zero (because it terminated with an error)
        assert handle.process.exitcode != 0

        # Reaching this assertion means that the parent process can continue execution
        # without being affected by errors in the child process
        assert True
