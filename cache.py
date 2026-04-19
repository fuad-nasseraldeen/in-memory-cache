"""
In-memory cache with:
- LRU eviction
- Optional TTL expiration
- Thread-safe access

Uses only Python standard library.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    """Single cache record."""

    value: Any
    expires_at: float | None  # Unix timestamp, or None for no expiration


class InMemoryCache:
    """
    Simple interview-friendly in-memory cache.

    Data structure:
    - OrderedDict for O(1)-ish key lookup and LRU ordering.
      Most recently used keys are moved to the end.
    - Lock to guard all read/write operations.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self._capacity = capacity
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._deletes = 0
        self._evictions = 0
        self._expirations = 0

    def set(self, key: str, value: Any, ttl_seconds: int | float | None = None) -> None:
        """
        Set a key to a value.
        ttl_seconds:
        - None => never expire
        - number <= 0 => immediate expiration
        """
        expires_at = None
        if ttl_seconds is not None:
            expires_at = time.time() + float(ttl_seconds)

        with self._lock:
            self._remove_expired_locked()

            # Insert/update key and mark as most recently used.
            self._store[key] = CacheEntry(value=value, expires_at=expires_at)
            self._store.move_to_end(key)
            self._writes += 1

            # Evict least recently used if over capacity.
            while len(self._store) > self._capacity:
                self._store.popitem(last=False)
                self._evictions += 1

    def get(self, key: str) -> Any | None:
        """
        Get value by key.
        Returns None on miss or expiration.
        On hit, updates LRU order.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if self._is_expired(entry):
                del self._store[key]
                self._expirations += 1
                self._misses += 1
                return None

            # Mark as most recently used on hit.
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def delete(self, key: str) -> bool:
        """Delete key if present. Returns True if deleted, else False."""
        with self._lock:
            deleted = self._store.pop(key, None) is not None
            if deleted:
                self._deletes += 1
            return deleted

    def size(self) -> int:
        """Return count of non-expired entries."""
        with self._lock:
            self._remove_expired_locked()
            return len(self._store)

    def get_stats(self) -> dict[str, int]:
        """Return cache statistics snapshot."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "deletes": self._deletes,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

    def stats(self) -> dict[str, int]:
        """
        Backward-compatible alias for older callers.
        Prefer get_stats().
        """
        snapshot = self.get_stats()
        return {
            **snapshot,
            # Legacy key kept for compatibility with existing benchmark/demo code.
            "expired_entries": snapshot["expirations"],
        }

    def reset_stats(self) -> None:
        """Reset all cache stats counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._writes = 0
            self._deletes = 0
            self._evictions = 0
            self._expirations = 0

    # ---- Internal helpers ----

    def _remove_expired_locked(self) -> None:
        """Remove all expired entries. Call only while holding lock."""
        now = time.time()
        expired_keys = [
            key
            for key, entry in self._store.items()
            if entry.expires_at is not None and now >= entry.expires_at
        ]
        for key in expired_keys:
            del self._store[key]
        self._expirations += len(expired_keys)

    @staticmethod
    def _is_expired(entry: CacheEntry) -> bool:
        return entry.expires_at is not None and time.time() >= entry.expires_at
