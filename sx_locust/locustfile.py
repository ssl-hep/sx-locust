import subprocess
import sys
from pathlib import Path
from locust import User, task, between
from locust.user.users import UserMeta
import logging

from sx_locust.config import get_config
from sx_locust.tests import ServiceXTest


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
                    
                    # Create a Locust task wrapper
                    def make_locust_task(method_name):
                        def locust_task(self):
                            # Execute the ServiceX test via subprocess
                            try:
                                result = subprocess.run(
                                    [sys.executable, "sx_locust/tests.py", "--query", method_name],
                                    capture_output=True,
                                    text=True,
                                    timeout=300
                                )
                                
                                if result.returncode != 0:
                                    self.logger.error(f"ServiceX test {method_name} failed with exit code {result.returncode}")
                                    self.logger.error(f"Stderr: {result.stderr}")
                                    raise Exception(f"ServiceX test {method_name} failed")
                                else:
                                    self.logger.info(f"ServiceX test {method_name} completed successfully")
                                    
                                return result
                                
                            except subprocess.TimeoutExpired:
                                self.logger.error(f"ServiceX test {method_name} timed out after 300 seconds")
                                raise Exception(f"ServiceX test {method_name} timed out")
                            except Exception as e:
                                self.logger.error(f"ServiceX test {method_name} failed: {e}")
                                raise
                        
                        # Set the required Locust task attributes
                        # locust_task._is_locust_task_method = True
                        # locust_task.locust_task_weight = 1
                        locust_task.__name__ = task_name
                        
                        return task(locust_task)
                    
                    # Add the task to the namespace before UserMeta sees it
                    namespace[task_name] = make_locust_task(attr_name)
        
        # Now let UserMeta do its normal processing with our tasks in the namespace
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


class ServiceXUser(ServiceXTest, User, metaclass=ServiceXUserMeta):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_config()
        self.servicex_config = self.config.servicex
        self.test_data_config = self.config.test_data
        self._setup_logging()

        # Set path to the worker script  
        self.worker_script_path = Path(__file__).parent / "tests.py"

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

    def on_start(self):
        """Called when a user starts"""
        self.logger.info("ServiceX user starting (subprocess mode)")
        self.logger.info(f"ServiceX endpoint: {self.servicex_config.endpoint}")
        self.logger.info(f"Worker script path: {self.worker_script_path}")

        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise

    def on_stop(self):
        """Called when a user stops"""
        self.logger.info("ServiceX user stopping")