# Production Optimizations Guide

This guide details the specific architectural decisions and production-grade optimizations implemented in the AI OCR Service to ensure high performance, low latency, and efficient resource utilization when deployed to cloud servers or containerized environments.

## 1. Fast JSON Serialization (ORJSONResponse)

**Implementation Location:** `app/main.py`
**Why it matters:**
Python's standard `json` module is relatively slow for large or deeply nested payloads. In a service that returns large arrays of prescription records or expansive search results, JSON serialization becomes a CPU bottleneck.
**The Solution:**
We integrated `orjson`, a highly optimized JSON library written in Rust. We customized FastAPI's `default_response_class` globally using `CustomORJSONResponse`. This guarantees that every endpoint natively serializes dictionaries, Pydantic records, and even nested array data types (NumPy) instantly.

## 2. Distributed Caching (Redis Cloud)

**Implementation Location:** `app/core/cache.py` and `app/api/search.py`
**Why it matters:**
Without an external distributed cache layer, scaling an application across multiple server instances means that cached search queries are not shared between instances, resulting in redundant LLM invocations and heavy Elasticsearch queries. Free-tier memory constraints also dictate that caching locally risks out-of-memory (OOM) fatal crashes.
**The Solution:**
We implemented asynchronous decorators leveraging the `redis.asyncio` provider. By explicitly routing the cache to Redislabs Cloud (`ConnectionPool.from_url`), horizontal scaling is unlocked. We protected read-heavy paths like `/autocomplete` and `/fuzzy` with `@cached(ttl=120)`.

## 3. High-Performance Connection Pooling

**Implementation Location:** `app/core/elasticsearch.py` and `app/core/cache.py`
**Why it matters:**
Opening a TCP socket and negotiating a TLS handshake for every incoming backend request creates massive network latency and starves server resource threads.
**The Solution:**
Both `AsyncElasticsearch` and the `redis` client instances are enforced globally as true singletons.

- The ES client guarantees up to `connections_per_node=25` pre-warmed TCP sockets.
- The Redis instance dictates a `max_connections=50` connection pool using automatic health keepalives.

## 4. Avoiding N+1 Queries

**Implementation Location:** `app/services/search/search_indexer.py`
**Why it matters:**
A classic ORM or search bottleneck exists when fetching a list of IDs (1 query) and then iterating over each ID to fetch its nested metadata (N queries).
**The Solution:**
The index schema is fully denormalized. A single `/all` query retrieves the parent prescription alongside the nested `medicine_names`, `diagnosis`, and `raw_text` simultaneously in the exact same index block retrieve (`_source` targeting), completely eradicating query multiplication arrays.

## 5. Strict Bound Pagination

**Implementation Location:** `app/services/search/search_indexer.py` (PaginationParams)
**Why it matters:**
Returning unbounded result sets (e.g., matching 10,000 records) severely degrades both client parsing speed and API transmission time.
**The Solution:**
Pydantic implicitly bounds all search `size`, `page`, and `page_size` routing parameters aggressively (`le=100`). `fuzzy_search` calculates hard Elasticsearch `from:` offset caps, preventing deep-pagination attacks.

## 6. GZip Payload Compression

**Implementation Location:** `app/main.py`
**Why it matters:**
Transmitting hundreds of kilobytes of uncompressed JSON across network topologies takes far longer than compressing the file Server-side and extracting it Client-side.
**The Solution:**
Enabled `GZipMiddleware` with a `minimum_size=1000` rule. Any payload over 1 Kilobyte utilizes dynamically injected stream compression, reducing payload transfer size by 70-85% depending on string redundancy.

## 7. Asynchronous Thread-Safe Logging (Loguru)

**Implementation Location:** `app/core/logger.py`
**Why it matters:**
Standard Python `logging` uses blocking IO hooks. If the host disk drive experiences latency while writing `app.log`, the entire synchronous Python Thread pauses, immediately stalling all active user API requests currently processing.
**The Solution:**
Replaced Python standard logging with `loguru` and enabled the `enqueue=True` parameter. All logging events are structurally dispatched to an asynchronous thread queue, freeing up the primary API web thread executing requests in under 1 microsecond while the background thread handles system IO operations linearly.
