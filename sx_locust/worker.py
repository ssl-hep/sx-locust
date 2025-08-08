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
    import io
    import tempfile

    class TeeStream:
        """Stream wrapper that writes to both original stream and captures content."""
        def __init__(self, original_stream, capture_stream):
            self.original = original_stream
            self.capture = capture_stream
            
        def write(self, data):
            # Write to both original (console) and capture stream
            self.original.write(data)
            self.original.flush()  # Ensure real-time output
            self.capture.write(data)
            return len(data)
            
        def flush(self):
            self.original.flush()
            self.capture.flush()
            
        def __getattr__(self, name):
            # Delegate other attributes to original stream
            return getattr(self.original, name)

    # Create string buffers to capture output
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    try:
        # Set up tee streams that write to both console and capture buffers
        sys.stdout = TeeStream(original_stdout, stdout_capture)
        sys.stderr = TeeStream(original_stderr, stderr_capture)
        
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
            # progress_bar='none'
        )

        # Get captured content
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()

        # Put successful result in queue
        result_queue.put({
            'success': True,
            'spec_keys': list(spec.keys()) if spec else None,
            'message': 'ServiceX query completed successfully',
            'stdout': stdout_content,
            'stderr': stderr_content
        })

    except Exception as e:
        # Get captured content even on failure
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()

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


