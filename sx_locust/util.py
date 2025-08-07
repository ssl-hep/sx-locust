import multiprocessing as mp

# Set multiprocessing start method to 'spawn' to avoid gevent conflicts
# This must be done before any multiprocessing operations
try:
    mp.set_start_method('spawn', force=True)
except RuntimeError:
    # Method already set, ignore
    pass

from locust.user.users import UserMeta
from sx_locust.worker import run_servicex_test_worker

"""
Multiprocessing worker module for ServiceX tests.
This module is separated to avoid import issues with multiprocessing 'spawn' method.
"""
import sys
from queue import Empty

from locust import task


# Create a Locust task wrapper
def make_locust_task(method_name):
    def locust_task(self):
        # Execute the ServiceX test via multiprocessing
        print(f"🚀 Starting ServiceX test: {method_name}", file=sys.stderr)

        result_queue = mp.Queue()
        error_queue = mp.Queue()

        # Create and start the worker process
        process = mp.Process(
            target=run_servicex_test_worker,
            args=(method_name, result_queue, error_queue)
        )

        try:
            process.start()

            # Wait for process to complete with timeout
            process.join(timeout=300)

            if process.is_alive():
                # Process timed out, terminate it
                process.terminate()
                process.join(timeout=5)  # Give it time to clean up
                if process.is_alive():
                    process.kill()  # Force kill if still alive

                print(f"⏰ ServiceX test {method_name} timed out after 300 seconds", file=sys.stderr)
                self.logger.error(f"ServiceX test {method_name} timed out after 300 seconds")
                raise Exception(f"ServiceX test {method_name} timed out")

            # Check if process completed successfully
            if process.exitcode != 0:
                # Try to get error information
                try:
                    error_info = error_queue.get_nowait()
                    print(f"❌ ServiceX test {method_name} failed: {error_info['error']}", file=sys.stderr)
                    self.logger.error(f"ServiceX test {method_name} failed: {error_info['error']}")
                    self.logger.error(f"Traceback: {error_info['traceback']}")

                    # Log captured stdout/stderr
                    if error_info.get('stdout'):
                        self.logger.info(f"ServiceX {method_name} stdout: {error_info['stdout']}")
                    if error_info.get('stderr'):
                        self.logger.error(f"ServiceX {method_name} stderr: {error_info['stderr']}")

                    raise Exception(f"ServiceX test {method_name} failed: {error_info['error']}")
                except Empty:
                    print(f"❌ ServiceX test {method_name} failed with exit code {process.exitcode}", file=sys.stderr)
                    self.logger.error(f"ServiceX test {method_name} failed with exit code {process.exitcode}")
                    raise Exception(f"ServiceX test {method_name} failed with exit code {process.exitcode}")

            # Get the successful result
            try:
                result_info = result_queue.get_nowait()
                if result_info['success']:
                    print(f"✅ ServiceX test {method_name} completed successfully", file=sys.stderr)
                    self.logger.info(f"ServiceX test {method_name} completed successfully")
                    self.logger.info(f"Result spec keys: {result_info['spec_keys']}")

                    # Log captured stdout/stderr
                    if result_info.get('stdout'):
                        self.logger.info(f"ServiceX {method_name} stdout: {result_info['stdout']}")
                    if result_info.get('stderr'):
                        self.logger.info(f"ServiceX {method_name} stderr: {result_info['stderr']}")

                    return result_info  # Return the info dict, not a non-existent 'result' key
                else:
                    print(f"❌ ServiceX test {method_name} unexpected error in result", file=sys.stderr)
                    raise Exception(f"Unexpected error in result: {result_info}")
            except Empty:
                print(f"⚠️ ServiceX test {method_name} completed but no result available", file=sys.stderr)
                self.logger.error(f"ServiceX test {method_name} completed but no result available")
                raise Exception(f"ServiceX test {method_name} completed but no result available")

        except Exception as e:
            # Ensure process is cleaned up
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()

            print(f"💥 ServiceX test {method_name} failed: {e}", file=sys.stderr)
            self.logger.error(f"ServiceX test {method_name} failed: {e}")
            raise
        finally:
            # Clean up queues
            try:
                while not result_queue.empty():
                    result_queue.get_nowait()
            except Empty:
                pass
            try:
                while not error_queue.empty():
                    error_queue.get_nowait()
            except Empty:
                pass

    # Set the required Locust task attributes
    # locust_task._is_locust_task_method = True
    # locust_task.locust_task_weight = 1
    locust_task.__name__ = method_name

    return task(locust_task)


class ServiceXUserMeta(UserMeta):
    """Metaclass that extends UserMeta to automatically convert @locust_test methods to Locust tasks"""

    def __new__(mcs, name, bases, namespace, **kwargs):
        # First, scan base classes for @locust_test methods and add them to namespace
        # before UserMeta processes the class
        for base in bases:
            for attr_name in dir(base):
                if attr_name.startswith('_'):
                    continue

                attr = getattr(base, attr_name)
                if (callable(attr) and
                        hasattr(attr, "__is_servicex_locust_test__") and
                        attr.__is_servicex_locust_test__):
                    task_name = f"{attr_name}_task"

                    # Add the task to the namespace before UserMeta sees it
                    namespace[task_name] = make_locust_task(attr_name)

        # Now let UserMeta do its normal processing with our tasks in the namespace
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls