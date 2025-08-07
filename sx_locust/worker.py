"""
Multiprocessing worker module for ServiceX tests.
This module is separated to avoid import issues with multiprocessing 'spawn' method.
"""
import traceback

def locust_task(func):
    """Decorator to mark a function as a ServiceX locust test."""
    func.__is_servicex_locust_test__ = True
    return func

def run_servicex_test_worker(method_name, result_queue, error_queue):
    """Worker function to run ServiceX tests in a separate process."""
    import os
    import sys
    import tempfile

    # Create temporary files to capture stdout and stderr
    stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)

    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # Redirect stdout and stderr to temp files
        sys.stdout = stdout_file
        sys.stderr = stderr_file
        # Import here to avoid circular imports and ensure fresh imports in worker process
        from sx_locust.tasks import ServiceXTasks

        # Create a fresh ServiceXTasks instance in the worker process
        test_instance = ServiceXTasks()

        # Get the test method
        test_method = getattr(test_instance, method_name)
        if not (hasattr(test_method, "__is_servicex_locust_test__") and
                test_method.__is_servicex_locust_test__):
            raise ValueError(f"Method {method_name} is not a valid ServiceX test")

        # Execute the test method to get the spec
        spec = test_method()

        # Import and run ServiceX deliver - this uses asyncio
        from servicex import deliver
        result = deliver(
            spec,
            ignore_local_cache=True,
            progress_bar='none'
        )

        # Flush and read captured output
        stdout_file.flush()
        stderr_file.flush()

        # Read the captured content
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout_content = stdout_file.read()
        stderr_content = stderr_file.read()

        # Put successful result in queue
        result_queue.put({
            'success': True,
            'spec_keys': list(spec.keys()) if spec else None,
            'message': 'ServiceX query completed successfully',
            'stdout': stdout_content,
            'stderr': stderr_content
        })

    except Exception as e:
        # Flush and read captured output even on failure
        stdout_file.flush()
        stderr_file.flush()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout_content = stdout_file.read()
        stderr_content = stderr_file.read()

        # Put error information in error queue
        error_queue.put({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'stdout': stdout_content,
            'stderr': stderr_content
        })
        # Exit with non-zero code to indicate failure (like subprocess would)
        sys.exit(1)
    finally:
        # Restore original stdout/stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # Clean up temp files
        try:
            stdout_file.close()
            os.unlink(stdout_file.name)
        except:
            pass
        try:
            stderr_file.close()
            os.unlink(stderr_file.name)
        except:
            pass


