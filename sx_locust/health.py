"""Health check utilities for ServiceX Locust testing."""

import logging
import time
from typing import Dict, Any, Optional
from .config import get_config

logger = logging.getLogger(__name__)


def check_servicex_health() -> Dict[str, Any]:
    """Check ServiceX service health."""
    config = get_config()
    
    try:
        # Import ServiceX components
        from servicex import query, dataset, deliver
        
        # Basic health check - try to create a simple query
        test_query = query.FuncADL_Uproot()
        
        return {
            "status": "healthy",
            "servicex_available": True,
            "endpoint": config.servicex.endpoint,
            "timestamp": time.time()
        }
        
    except ImportError as e:
        logger.warning(f"ServiceX not available: {e}")
        return {
            "status": "degraded",
            "servicex_available": False,
            "error": str(e),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"ServiceX health check failed: {e}")
        return {
            "status": "unhealthy",
            "servicex_available": False,
            "error": str(e),
            "timestamp": time.time()
        }


def check_config_health() -> Dict[str, Any]:
    """Check configuration health."""
    try:
        config = get_config()
        config.validate()
        
        return {
            "status": "healthy",
            "config_valid": True,
            "log_level": config.log_level,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Configuration health check failed: {e}")
        return {
            "status": "unhealthy",
            "config_valid": False,
            "error": str(e),
            "timestamp": time.time()
        }


def full_health_check() -> Dict[str, Any]:
    """Perform a complete health check."""
    servicex_health = check_servicex_health()
    config_health = check_config_health()
    
    overall_status = "healthy"
    if servicex_health["status"] == "unhealthy" or config_health["status"] == "unhealthy":
        overall_status = "unhealthy"
    elif servicex_health["status"] == "degraded" or config_health["status"] == "degraded":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "servicex": servicex_health,
        "config": config_health,
        "timestamp": time.time()
    }