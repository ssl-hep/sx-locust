from locust import User, between
from sx_locust.config import get_config
import logging

from sx_locust.tests import ServiceXTest
from sx_locust.util import ServiceXUserMeta


class ServiceXUser(ServiceXTest, User, metaclass=ServiceXUserMeta):
    wait_time = between(1, 5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = get_config()
        self.servicex_config = self.config.servicex
        self.test_data_config = self.config.test_data
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))

    def on_start(self):
        """Called when a user starts"""
        self.logger.info("ServiceX user starting (multiprocessing mode)")
        self.logger.info(f"ServiceX endpoint: {self.servicex_config.endpoint}")

        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise

    def on_stop(self):
        """Called when a user stops"""
        self.logger.info("ServiceX user stopping")