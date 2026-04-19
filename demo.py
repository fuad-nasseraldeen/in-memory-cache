import threading
import time

from cache import InMemoryCache


def log(title: str) -> None:
    print(f"\n=== {title} ===")


def show_get(cache: InMemoryCache, key: str, expected_reason: str | None = None) -> None:
    value = cache.get(key)
    if value is None:
        if expected_reason:
            print(f"MISS  key={key!r} ({expected_reason})")
        else:
            print(f"MISS  key={key!r}")
    else:
        print(f"HIT   key={key!r}, value={value!r}")


def basic_lru_and_ttl_demo() -> None:
    cache = InMemoryCache(capacity=3)

    log("1) Add Multiple Keys")
    cache.set("A", "apple")
    cache.set("B", "banana")
    cache.set("C", "cherry")
    print(f"size={cache.size()} (expected 3)")

    log("2) Access Key To Update LRU Order")
    show_get(cache, "A")  # A becomes most recently used.

    log("3) Trigger Eviction When Capacity Is Reached")
    print("Adding key 'D'. Capacity is 3, so one key must be evicted.")
    print("Expected evicted key: 'B' (least recently used after touching 'A').")
    cache.set("D", "dragonfruit")
    print(f"size={cache.size()} (expected 3)")
    show_get(cache, "B", expected_reason="evicted entry")
    show_get(cache, "A")
    show_get(cache, "C")
    show_get(cache, "D")

    log("4) TTL Expiration")
    cache.set("TEMP", "short-lived", ttl_seconds=2)
    show_get(cache, "TEMP")
    print("Sleeping for 3 seconds so TEMP expires...")
    time.sleep(3)
    show_get(cache, "TEMP", expected_reason="expired entry")

    log("5) Manual Delete")
    deleted = cache.delete("C")
    print(f"delete('C') -> {deleted}")
    show_get(cache, "C", expected_reason="deleted")
    print(f"final size={cache.size()}")


def thread_safety_demo() -> None:
    """
    Higher-contention concurrency demo to show lock-based safety.
    """
    cache = InMemoryCache(capacity=40)
    cache.reset_stats()

    key_space = 30  # Intentionally small so threads overlap heavily.
    writer_threads = 6
    reader_threads = 6
    ops_per_thread = 500
    start_barrier = threading.Barrier(writer_threads + reader_threads)

    worker_summary_lock = threading.Lock()
    writer_ops_total = 0
    reader_ops_total = 0

    def writer(thread_id: int) -> None:
        nonlocal writer_ops_total
        start_barrier.wait()
        for i in range(ops_per_thread):
            key = f"shared-{(i + thread_id) % key_space}"
            value = f"writer{thread_id}-v{i}"
            ttl = 1.2 if i % 25 == 0 else None
            cache.set(key, value, ttl_seconds=ttl)
        with worker_summary_lock:
            writer_ops_total += ops_per_thread

    def reader(thread_id: int) -> None:
        nonlocal reader_ops_total
        start_barrier.wait()
        for i in range(ops_per_thread):
            key = f"shared-{(i + (thread_id * 3)) % key_space}"
            _ = cache.get(key)
            if i % 120 == 0:
                # Encourage natural interleaving with writers.
                time.sleep(0.001)
        with worker_summary_lock:
            reader_ops_total += ops_per_thread

    log("6) High-Contention Thread-Safe Access")
    print(
        f"Starting {writer_threads} writers + {reader_threads} readers "
        f"over {key_space} overlapping keys..."
    )
    threads: list[threading.Thread] = []
    for tid in range(writer_threads):
        threads.append(threading.Thread(target=writer, args=(tid,)))
    for tid in range(reader_threads):
        threads.append(threading.Thread(target=reader, args=(tid,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_size = cache.size()
    stats = cache.get_stats()

    print("Concurrent run completed without crashes or data-structure errors.")
    print(f"writer ops: {writer_ops_total}, reader ops: {reader_ops_total}")
    print(f"final size: {final_size} (capacity={40})")
    print("final stats:")
    print(f"  hits={stats['hits']}")
    print(f"  misses={stats['misses']}")
    print(f"  writes={stats['writes']}")
    print(f"  deletes={stats['deletes']}")
    print(f"  evictions={stats['evictions']}")
    print(f"  expirations={stats['expirations']}")


if __name__ == "__main__":
    print("In-Memory Cache Demo")
    basic_lru_and_ttl_demo()
    thread_safety_demo()
