"""
redis_store.py
Redis-backed job store — drop-in replacement for the in-memory RESULTS dict.
Jobs expire automatically after JOB_TTL_SECONDS (default 24 hours).
"""
import os
import json
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

REDIS_URL       = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", str(24 * 60 * 60)))  # 24 hours
JOB_KEY_PREFIX  = "job:"

# ── Client ─────────────────────────────────────────────────────────────────────

def _make_client() -> redis.Redis:
    """Create and validate a Redis client at startup."""
    client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    try:
        client.ping()
        logger.info("Redis connected: %s", REDIS_URL)
    except redis.ConnectionError as exc:
        raise RuntimeError(
            f"Cannot connect to Redis at {REDIS_URL}. "
            "Make sure Redis is running and REDIS_URL is set correctly."
        ) from exc
    return client


_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    """Return the shared Redis client, initialising it on first call."""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


# ── Key helpers ────────────────────────────────────────────────────────────────

def _key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


# ── Public API — mirrors the old RESULTS dict interface ───────────────────────

def set_job(job_id: str, data: dict, ttl: int = JOB_TTL_SECONDS) -> None:
    """
    Store or update a job. Resets the TTL on every write.
    Raises RedisError on failure.
    """
    get_client().setex(_key(job_id), ttl, json.dumps(data, ensure_ascii=False))


def get_job(job_id: str) -> Optional[dict]:
    """
    Retrieve a job by ID.
    Returns None if the job doesn't exist or has expired.
    """
    raw = get_client().get(_key(job_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Corrupt job data for job_id=%s", job_id)
        return None


def delete_job(job_id: str) -> bool:
    """
    Delete a job. Returns True if it existed, False if not found.
    """
    return bool(get_client().delete(_key(job_id)))


def job_exists(job_id: str) -> bool:
    """Check if a job exists without fetching its full data."""
    return bool(get_client().exists(_key(job_id)))


def update_job_status(job_id: str, status: str, extra: Optional[dict] = None) -> None:
    """
    Convenience helper — update just the status field of an existing job.
    If the job doesn't exist, creates a minimal record.
    """
    job = get_job(job_id) or {}
    job["status"] = status
    if extra:
        job.update(extra)
    set_job(job_id, job)


def list_jobs(limit: int = 100) -> list[str]:
    """
    Return up to `limit` active job IDs.
    Intended for admin/debug use only — SCAN is O(N) over the keyspace.
    """
    client = get_client()
    job_ids = []
    cursor = 0
    pattern = f"{JOB_KEY_PREFIX}*"
    while True:
        cursor, keys = client.scan(cursor, match=pattern, count=200)
        for k in keys:
            job_ids.append(k[len(JOB_KEY_PREFIX):])
            if len(job_ids) >= limit:
                return job_ids
        if cursor == 0:
            break
    return job_ids


def health_check() -> dict:
    """
    Return Redis health info for the /health endpoint.
    """
    try:
        client = get_client()
        info   = client.info("server")
        return {
            "status":  "ok",
            "version": info.get("redis_version", "unknown"),
            "ping":    client.ping(),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
