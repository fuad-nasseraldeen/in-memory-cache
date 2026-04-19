# In-Memory Cache

Lightweight, production-style in-memory cache built with Python standard library only.  
Implements LRU eviction, per-key TTL, thread-safe operations, and basic performance benchmarking.

## Project Motivation

This project demonstrates practical cache design tradeoffs that appear in backend systems and interviews:
- bounded memory usage
- stale data control
- concurrent access safety
- measurable performance impact

## Architecture Overview

- `cache.py`: `InMemoryCache` implementation using `OrderedDict` + `threading.Lock`
- `demo.py`: behavior walkthrough (hits, misses, expirations, evictions)
- `benchmark.py`: deterministic A/B benchmark (`without cache` vs `with cache`)

Core API:
- `set(key, value, ttl_seconds=None)`
- `get(key)`
- `delete(key)`
- `size()`
- `get_stats()`

## Why LRU Was Chosen

LRU is a strong default for bounded caches because recently accessed items are more likely to be reused soon (temporal locality).  
Using `OrderedDict` keeps the implementation simple and readable while supporting efficient recency updates and least-recent eviction.

## Why TTL Matters

TTL prevents stale values from living indefinitely and bounds data freshness without external invalidation signals.  
This is especially useful when source data changes over time or when cache correctness depends on eventual refresh.

## Synchronization Approach

All public operations are guarded by a single `threading.Lock`:
- `set`, `get`, `delete`, `size`, `get_stats`

This favors correctness and simplicity over maximum parallel throughput, which is appropriate for an interview-friendly baseline.

## Benchmark Methodology

`benchmark.py` uses a deterministic workload with repeated key access and churn:
- Simulates expensive reads via fixed `time.sleep(...)`
- Runs two modes:
  - without cache: always pay expensive read cost
  - with cache: cache lookup first, fallback to expensive read on miss
- Reports:
  - total execution time
  - hits, misses
  - evictions
  - expirations

## Benchmark Results

Sample run (local):

| Metric | Without Cache | With Cache |
|---|---:|---:|
| Total time (s) | 0.4809 | 0.2851 |
| Cache hits | 0 | 138 |
| Cache misses | 210 | 72 |
| Evictions | 0 | 44 |
| Expired entries | 0 | 9 |
| Speedup | 1.00x | 1.69x |

Results vary by machine, but cached mode should consistently reduce total time for repeated-access workloads.

## Limitations

- Process-local memory only (not shared across processes/hosts)
- No persistence or recovery across restarts
- Single global lock may limit throughput under heavy contention
- No background cleanup thread; expiration is lazy
- No advanced eviction policies beyond LRU

## Future Improvements

- Optional read/write locks or lock striping for higher concurrency
- Background expiration sweeper
- Metrics export hooks (Prometheus/OpenTelemetry style integration)
- Size-aware eviction (bytes-based) in addition to entry count
- Optional async interface for async applications

## Run

```bash
python demo.py
python benchmark.py
```
