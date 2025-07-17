"""Configuration management for ServiceX Locust testing."""

import os
import logging
from typing import List, Optional, Any
from dataclasses import dataclass, field
import yaml
from pathlib import Path


@dataclass
class ServiceXConfig:
    """Configuration for ServiceX operations."""
    endpoint: str
    timeout: int = 60
    max_retries: int = 3
    auth_token: Optional[str] = None
    auth_type: str = "token"


@dataclass
class LoadTestConfig:
    """Configuration for load testing parameters."""
    concurrent_users: int = 10
    spawn_rate: int = 1
    run_time: str = "60s"
    host: str = "http://localhost:8089"


@dataclass
class TestDataConfig:
    """Configuration for test data files."""
    atlas_files: List[str] = field(default_factory=list)
    cms_files: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration class."""
    servicex: ServiceXConfig
    load_test: LoadTestConfig
    test_data: TestDataConfig
    log_level: str = "INFO"
    cache_path: str = "/tmp/servicex_cache"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        servicex_config = ServiceXConfig(
            endpoint=os.getenv("SERVICEX_ENDPOINT", "https://servicex.example.com"),
            timeout=int(os.getenv("SERVICEX_TIMEOUT", "60")),
            max_retries=int(os.getenv("SERVICEX_MAX_RETRIES", "3")),
            auth_token=os.getenv("SERVICEX_TOKEN"),
            auth_type=os.getenv("SERVICEX_AUTH_TYPE", "token"),
        )
        
        load_test_config = LoadTestConfig(
            concurrent_users=int(os.getenv("LOCUST_USERS", "10")),
            spawn_rate=int(os.getenv("LOCUST_SPAWN_RATE", "1")),
            run_time=os.getenv("LOCUST_RUN_TIME", "60s"),
            host=os.getenv("LOCUST_HOST", "http://localhost:8089"),
        )
        
        # Load test data from environment (comma-separated)
        atlas_files = []
        if os.getenv("ATLAS_TEST_FILES"):
            atlas_files = [f.strip() for f in os.getenv("ATLAS_TEST_FILES", "").split(",") if f.strip()]
        
        cms_files = []
        if os.getenv("CMS_TEST_FILES"):
            cms_files = [f.strip() for f in os.getenv("CMS_TEST_FILES", "").split(",") if f.strip()]
        
        test_data_config = TestDataConfig(
            atlas_files=atlas_files,
            cms_files=cms_files,
        )
        
        return cls(
            servicex=servicex_config,
            load_test=load_test_config,
            test_data=test_data_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cache_path=os.getenv("SERVICEX_CACHE_PATH", "/tmp/servicex_cache"),
        )

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file with environment variable substitution."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Substitute environment variables in the config
        config_data = cls._substitute_env_vars(config_data)
        
        # Extract configurations
        servicex_data = config_data.get("servicex", {})
        load_test_data = config_data.get("load_testing", {})
        test_data_data = config_data.get("test_data", {})
        
        servicex_config = ServiceXConfig(
            endpoint=servicex_data.get("endpoint", "https://servicex.example.com"),
            timeout=servicex_data.get("timeout", 60),
            max_retries=servicex_data.get("max_retries", 3),
            auth_token=servicex_data.get("auth_token"),
            auth_type=servicex_data.get("auth_type", "token"),
        )
        
        load_test_config = LoadTestConfig(
            concurrent_users=load_test_data.get("concurrent_users", 10),
            spawn_rate=load_test_data.get("spawn_rate", 1),
            run_time=load_test_data.get("run_time", "60s"),
            host=load_test_data.get("host", "http://localhost:8089"),
        )
        
        test_data_config = TestDataConfig(
            atlas_files=test_data_data.get("atlas_files", []),
            cms_files=test_data_data.get("cms_files", []),
        )
        
        return cls(
            servicex=servicex_config,
            load_test=load_test_config,
            test_data=test_data_config,
            log_level=config_data.get("log_level", "INFO"),
            cache_path=config_data.get("cache_path", "/tmp/servicex_cache"),
        )

    @staticmethod
    def _substitute_env_vars(obj: Any) -> Any:
        """Recursively substitute environment variables in configuration."""
        if isinstance(obj, dict):
            return {k: Config._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Config._substitute_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            # Simple environment variable substitution
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, obj)
            for match in matches:
                # Support default values: ${VAR:-default}
                if ':-' in match:
                    var_name, default_value = match.split(':-', 1)
                    env_value = os.getenv(var_name, default_value)
                else:
                    env_value = os.getenv(match, '')
                obj = obj.replace(f'${{{match}}}', env_value)
            return obj
        return obj

    def validate(self) -> None:
        """Validate configuration values."""
        errors = []
        
        # Validate ServiceX configuration
        if not self.servicex.endpoint:
            errors.append("ServiceX endpoint is required")
        
        if self.servicex.timeout <= 0:
            errors.append("ServiceX timeout must be positive")
        
        if self.servicex.max_retries < 0:
            errors.append("ServiceX max_retries must be non-negative")
        
        # Validate load test configuration
        if self.load_test.concurrent_users <= 0:
            errors.append("Concurrent users must be positive")
        
        if self.load_test.spawn_rate <= 0:
            errors.append("Spawn rate must be positive")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")
        
        if errors:
            raise ValueError("Configuration validation failed: " + "; ".join(errors))

    def setup_logging(self) -> None:
        """Set up logging based on configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/tmp/sx-locust.log')
            ]
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        # Try to load from file first, then fall back to environment
        config_file = os.getenv("CONFIG_FILE", "../servicex.yaml")
        if os.path.exists(config_file):
            _config = Config.from_file(config_file)
        else:
            _config = Config.from_env()
        
        _config.validate()
        _config.setup_logging()
    
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance (mainly for testing)."""
    global _config
    _config = config