"""
Risk Sentinel — Infrastructure Security, Authentication & Rate Limiting
Provides:
1. Constant-time API Key and Bearer token verification.
2. Thread-safe in-memory sliding-window rate limiter with TTL eviction.
3. Standard HTTP security headers middleware.
4. Clean separation between local development mode and enforced authentication.
"""

import os
import time
import secrets
import threading
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

# Header schemes
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER_AUTH = HTTPBearer(auto_error=False)

def get_configured_api_key() -> Optional[str]:
    """Retrieves configured API key from environment, if any."""
    return os.getenv("RISK_SENTINEL_API_KEY", None)

def is_auth_enforced() -> bool:
    """Returns True if API authentication is explicitly enforced."""
    flag = os.getenv("RISK_SENTINEL_REQUIRE_AUTH", "false").lower()
    return flag in ("1", "true", "yes") or get_configured_api_key() is not None

def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(BEARER_AUTH)
) -> bool:
    """
    Validates API key or Bearer token using constant-time comparison.
    If authentication is not enforced in local demo mode, requests pass through.
    """
    configured_key = get_configured_api_key()
    
    # If auth is not enforced and no key is configured, permit for local demo
    if not is_auth_enforced() and not configured_key:
        return True

    # Check X-API-Key header first
    provided_token = api_key
    
    # Check Bearer token if X-API-Key was not present
    if not provided_token and bearer and bearer.credentials:
        provided_token = bearer.credentials

    if not provided_token or not configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API credentials.",
            headers={"WWW-Authenticate": "Bearer or X-API-Key"}
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_token.strip(), configured_key.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or token.",
            headers={"WWW-Authenticate": "Bearer or X-API-Key"}
        )

    return True

class InMemoryRateLimiter:
    """
    Thread-safe, sliding-window in-memory rate limiter.
    Note: In-memory rate limiting protects a single process.
    Distributed deployments should use a shared limiter such as Redis.
    """
    def __init__(self, requests_per_window: int = 120, window_seconds: int = 60, max_tracked_ips: int = 10000):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.max_tracked_ips = max_tracked_ips
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = {}

    def check_rate_limit(self, client_identifier: str) -> None:
        """
        Checks whether client has exceeded allowed requests in current sliding window.
        Evicts expired timestamps to prevent unbounded memory growth.
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Memory safety: prune inactive clients if cache reaches threshold
            if len(self._records) >= self.max_tracked_ips:
                self._prune_inactive_clients(window_start)

            client_history = self._records.setdefault(client_identifier, [])
            
            # Remove timestamps outside sliding window
            self._records[client_identifier] = [t for t in client_history if t > window_start]
            valid_requests = self._records[client_identifier]

            if len(valid_requests) >= self.requests_per_window:
                earliest_request = valid_requests[0]
                retry_after = max(1, int(earliest_request + self.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit of {self.requests_per_window} requests per {self.window_seconds}s exceeded.",
                    headers={"Retry-After": str(retry_after)}
                )

            self._records[client_identifier].append(now)

    def _prune_inactive_clients(self, window_start: float) -> None:
        """Evicts clients with no requests in current sliding window."""
        to_delete = []
        for k, v in self._records.items():
            valid = [t for t in v if t > window_start]
            if not valid:
                to_delete.append(k)
            else:
                self._records[k] = valid
        for k in to_delete:
            del self._records[k]

    def reset(self) -> None:
        """Resets rate limiter records (used in tests)."""
        with self._lock:
            self._records.clear()

# Global in-memory rate limiter instance
default_rate_limiter = InMemoryRateLimiter(requests_per_window=300, window_seconds=60)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all HTTP responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
