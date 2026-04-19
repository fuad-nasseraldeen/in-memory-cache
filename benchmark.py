"""
Deterministic benchmark for the In-Memory Cache project.

Compares two modes:
1) without cache
2) with cache

Reports:
- total execution time
- cache hits
- cache misses
- evictions
- expirations
- speedup ratio
"""

from __future__ import annotations

import time
from cache import InMemoryCache


def expensive_data_access(key: int) -> str:
    """
    Simulate expensive work (DB/API/disk).
    Fixed sleep keeps benchmark deterministic and simple.
    """
    time.sleep(0.002)
    return f"value-{key}"


def build_workload() -> list[int]:
    """
    Deterministic access pattern:
    - Repeated hot keys for potential cache hits
    - Wider key range to force LRU evictions
    """
    hot_keys = [0, 1, 2, 3, 4] * 20
    churn_keys = list(range(5, 35)) * 2
    tail_hot = [0, 1, 2, 3, 4] * 10
    return hot_keys + churn_keys + tail_hot


def ttl_for_key(key: int) -> float | None:
    """
    Some keys get short TTL so expiration can be observed.
    """
    if key % 9 == 0:
        return 0.03
    return None


def run_without_cache(workload: list[int]) -> dict[str, float | int]:
    start = time.perf_counter()
    for key in workload:
        _ = expensive_data_access(key)
    elapsed = time.perf_counter() - start

    op_count = len(workload)
    return {
        "time_seconds": elapsed,
        "hits": 0,
        "misses": op_count,
        "evictions": 0,
        "expirations": 0,
    }


def run_with_cache(workload: list[int]) -> dict[str, float | int]:
    cache = InMemoryCache(capacity=20)
    cache.reset_stats()

    start = time.perf_counter()

    for i, key in enumerate(workload, start=1):
        value = cache.get(str(key))
        if value is None:
            loaded = expensive_data_access(key)
            cache.set(str(key), loaded, ttl_seconds=ttl_for_key(key))

        # Deterministic pause points to let short-TTL entries expire.
        if i % 60 == 0:
            time.sleep(0.04)

    # Trigger cleanup so expired count includes entries that expired but were never read again.
    _ = cache.size()

    elapsed = time.perf_counter() - start
    metrics = cache.get_stats()
    metrics["time_seconds"] = elapsed
    return metrics


def print_report(no_cache: dict[str, float | int], with_cache: dict[str, float | int]) -> None:
    total_requests = int(no_cache["misses"])
    no_cache_time = float(no_cache["time_seconds"])
    with_cache_time = float(with_cache["time_seconds"])
    speedup = no_cache_time / with_cache_time if with_cache_time > 0 else 0.0
    improvement_pct = (
        ((no_cache_time - with_cache_time) / no_cache_time) * 100.0 if no_cache_time > 0 else 0.0
    )
    avg_latency_no_cache_ms = (no_cache_time / total_requests) * 1000.0 if total_requests > 0 else 0.0
    avg_latency_with_cache_ms = (
        (with_cache_time / total_requests) * 1000.0 if total_requests > 0 else 0.0
    )

    print("\nIn-Memory Cache Benchmark")
    print("=" * 60)
    print(f"{'Metric':<20}{'Without Cache':>18}{'With Cache':>18}")
    print("-" * 60)
    print(f"{'Total time (s)':<20}{no_cache_time:>18.4f}{with_cache_time:>18.4f}")
    print(
        f"{'Avg latency (ms)':<20}"
        f"{avg_latency_no_cache_ms:>18.4f}"
        f"{avg_latency_with_cache_ms:>18.4f}"
    )
    print(f"{'Cache hits':<20}{no_cache['hits']:>18}{with_cache['hits']:>18}")
    print(f"{'Cache misses':<20}{no_cache['misses']:>18}{with_cache['misses']:>18}")
    print(f"{'Evictions':<20}{no_cache['evictions']:>18}{with_cache['evictions']:>18}")
    print(f"{'Expirations':<20}{no_cache['expirations']:>18}{with_cache['expirations']:>18}")
    print("-" * 60)
    print(f"Speedup ratio (without/with): {speedup:.2f}x")
    print(f"Execution time improvement: {improvement_pct:.2f}%")


def main() -> None:
    workload = build_workload()
    no_cache_metrics = run_without_cache(workload)
    with_cache_metrics = run_with_cache(workload)
    print_report(no_cache_metrics, with_cache_metrics)


if __name__ == "__main__":
    main()
