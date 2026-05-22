"""
tests/test_redis_store.py
Unit tests for redis_store.py — all Redis calls are mocked.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import json
import pytest
from unittest.mock import MagicMock, patch

import redis_store as store_module
from redis_store import (
    set_job,
    get_job,
    delete_job,
    job_exists,
    update_job_status,
    list_jobs,
    health_check,
    _key,
    JOB_KEY_PREFIX,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_redis_client():
    """Replace the module-level Redis client with a MagicMock for every test."""
    mock = MagicMock()
    mock.ping.return_value = True
    with patch.object(store_module, "_client", mock):
        yield mock


SAMPLE_JOB = {
    "status":            "done",
    "detected_language": "hi",
    "segments":          [],
    "full_text":         "नमस्ते",
}


# ── Key helper ─────────────────────────────────────────────────────────────────

class TestKeyHelper:
    def test_prefixes_job_id(self):
        assert _key("abc123") == f"{JOB_KEY_PREFIX}abc123"

    def test_different_ids_produce_different_keys(self):
        assert _key("job1") != _key("job2")


# ── set_job ────────────────────────────────────────────────────────────────────

class TestSetJob:
    def test_calls_setex(self, mock_redis_client):
        set_job("job1", SAMPLE_JOB)
        mock_redis_client.setex.assert_called_once()

    def test_uses_correct_key(self, mock_redis_client):
        set_job("job1", SAMPLE_JOB)
        args = mock_redis_client.setex.call_args[0]
        assert args[0] == _key("job1")

    def test_json_serialises_devanagari(self, mock_redis_client):
        set_job("job1", SAMPLE_JOB)
        args  = mock_redis_client.setex.call_args[0]
        value = args[2]
        parsed = json.loads(value)
        assert parsed["full_text"] == "नमस्ते"

    def test_custom_ttl_passed_to_setex(self, mock_redis_client):
        set_job("job1", SAMPLE_JOB, ttl=3600)
        args = mock_redis_client.setex.call_args[0]
        assert args[1] == 3600


# ── get_job ────────────────────────────────────────────────────────────────────

class TestGetJob:
    def test_returns_dict_when_exists(self, mock_redis_client):
        mock_redis_client.get.return_value = json.dumps(SAMPLE_JOB)
        result = get_job("job1")
        assert result == SAMPLE_JOB

    def test_returns_none_when_missing(self, mock_redis_client):
        mock_redis_client.get.return_value = None
        result = get_job("job1")
        assert result is None

    def test_returns_none_on_corrupt_json(self, mock_redis_client):
        mock_redis_client.get.return_value = "not-valid-json{{{"
        result = get_job("job1")
        assert result is None

    def test_uses_correct_key(self, mock_redis_client):
        mock_redis_client.get.return_value = None
        get_job("job42")
        mock_redis_client.get.assert_called_once_with(_key("job42"))


# ── delete_job ─────────────────────────────────────────────────────────────────

class TestDeleteJob:
    def test_returns_true_when_deleted(self, mock_redis_client):
        mock_redis_client.delete.return_value = 1
        assert delete_job("job1") is True

    def test_returns_false_when_not_found(self, mock_redis_client):
        mock_redis_client.delete.return_value = 0
        assert delete_job("job1") is False

    def test_uses_correct_key(self, mock_redis_client):
        mock_redis_client.delete.return_value = 1
        delete_job("job99")
        mock_redis_client.delete.assert_called_once_with(_key("job99"))


# ── job_exists ─────────────────────────────────────────────────────────────────

class TestJobExists:
    def test_returns_true_when_exists(self, mock_redis_client):
        mock_redis_client.exists.return_value = 1
        assert job_exists("job1") is True

    def test_returns_false_when_missing(self, mock_redis_client):
        mock_redis_client.exists.return_value = 0
        assert job_exists("job1") is False


# ── update_job_status ─────────────────────────────────────────────────────────

class TestUpdateJobStatus:
    def test_updates_existing_job_status(self, mock_redis_client):
        existing = {"status": "processing", "job_id": "job1"}
        mock_redis_client.get.return_value = json.dumps(existing)

        update_job_status("job1", "done")

        written = json.loads(mock_redis_client.setex.call_args[0][2])
        assert written["status"] == "done"
        assert written["job_id"] == "job1"  # existing fields preserved

    def test_creates_new_record_if_missing(self, mock_redis_client):
        mock_redis_client.get.return_value = None

        update_job_status("new-job", "processing")

        written = json.loads(mock_redis_client.setex.call_args[0][2])
        assert written["status"] == "processing"

    def test_merges_extra_fields(self, mock_redis_client):
        existing = {"status": "processing"}
        mock_redis_client.get.return_value = json.dumps(existing)

        update_job_status("job1", "done", extra={"result": "ok", "count": 3})

        written = json.loads(mock_redis_client.setex.call_args[0][2])
        assert written["result"] == "ok"
        assert written["count"]  == 3


# ── list_jobs ─────────────────────────────────────────────────────────────────

class TestListJobs:
    def test_returns_job_ids_without_prefix(self, mock_redis_client):
        keys = [f"{JOB_KEY_PREFIX}job1", f"{JOB_KEY_PREFIX}job2"]
        # scan returns (cursor, keys); cursor=0 means done
        mock_redis_client.scan.return_value = (0, keys)

        result = list_jobs()
        assert "job1" in result
        assert "job2" in result

    def test_respects_limit(self, mock_redis_client):
        keys = [f"{JOB_KEY_PREFIX}job{i}" for i in range(50)]
        mock_redis_client.scan.return_value = (0, keys)

        result = list_jobs(limit=5)
        assert len(result) <= 5

    def test_empty_when_no_jobs(self, mock_redis_client):
        mock_redis_client.scan.return_value = (0, [])
        result = list_jobs()
        assert result == []


# ── health_check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_returns_ok_when_connected(self, mock_redis_client):
        mock_redis_client.info.return_value = {"redis_version": "7.2.0"}
        mock_redis_client.ping.return_value  = True

        result = health_check()
        assert result["status"]  == "ok"
        assert result["version"] == "7.2.0"
        assert result["ping"]    is True

    def test_returns_error_on_connection_failure(self, mock_redis_client):
        mock_redis_client.info.side_effect = Exception("Connection refused")

        result = health_check()
        assert result["status"] == "error"
        assert "Connection refused" in result["detail"]
