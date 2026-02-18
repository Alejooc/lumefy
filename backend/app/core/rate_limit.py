"""
Rate Limiting configuration via slowapi.
Provides a pre-configured Limiter instance and key functions.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance — keyed by client IP
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
