"""
TTL-based in-memory cache for analysis results.

Avoids re-fetching and re-analyzing URLs that were recently processed,
which reduces LLM API costs and latency for repeated requests.

Usage:
    from app.services.cache_service import analysis_cache

    result = await analysis_cache.get(url)
    if result is None:
        result = ...expensive work...
        await analysis_cache.set(url, result)
"""
import asyncio
import logging
import time
from typing import Any, Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Thread-safe, TTL-based in-memory cache."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Key normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(url: str) -> str:
        """
        Normalise a URL to a stable cache key.

        Strips trailing slashes and lowercases the scheme + host so that
        ``https://Example.com/`` and ``https://example.com`` share a key.
        The path, query, and fragment are kept as-is because they can
        legitimately point to different pages.
        """
        try:
            parsed = urlparse(url)
            normalised = parsed._replace(
                scheme=parsed.scheme.lower(),
                netloc=parsed.netloc.lower(),
                path=parsed.path.rstrip("/") or "/",
            )
            return normalised.geturl()
        except Exception:
            return url.strip().rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, url: str) -> Optional[Any]:
        """Return the cached value for *url*, or ``None`` if missing / expired."""
        key = self._normalise(url)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                logger.debug("Cache expired for %s", key)
                return None
            logger.info("Cache hit for %s", key)
            return value

    async def set(self, url: str, value: Any) -> None:
        """Store *value* for *url* with the configured TTL."""
        key = self._normalise(url)
        async with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)
        logger.info("Cached result for %s (TTL %ds)", key, self._ttl)

    async def invalidate(self, url: str) -> bool:
        """Remove the cached entry for *url*. Returns True if an entry existed."""
        key = self._normalise(url)
        async with self._lock:
            if key in self._store:
                del self._store[key]
                logger.info("Cache invalidated for %s", key)
                return True
            return False

    async def clear(self) -> None:
        """Flush the entire cache (useful in tests)."""
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Current number of cached entries (including not-yet-expired ones)."""
        return len(self._store)


# ---------------------------------------------------------------------------
# Singleton — shared across all requests in this process
# ---------------------------------------------------------------------------

#: Global cache instance.  TTL is taken from CACHE_TTL_SECONDS in settings
#: (defaults to 3600 s = 1 hour).
analysis_cache = CacheService(ttl_seconds=getattr(settings, "CACHE_TTL_SECONDS", 3600))
