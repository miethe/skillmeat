"""Unit tests for burst detection components.

Tests RequestFingerprint, SlidingWindowTracker, and burst detection logic.
"""

import time
from typing import Dict

import pytest
from fastapi import Request
from fastapi.datastructures import QueryParams
from starlette.datastructures import Headers

from skillmeat.api.middleware.burst_detection import (
    RequestFingerprint,
    RequestRecord,
    SlidingWindowTracker,
    create_fingerprint,
)


class TestRequestFingerprint:
    """Tests for RequestFingerprint hashing and equality."""

    def test_fingerprint_equality(self):
        """Test that fingerprints with same values are equal."""
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("GET", "/api/test", "abc123")

        assert fp1 == fp2
        assert hash(fp1) == hash(fp2)

    def test_fingerprint_inequality_endpoint(self):
        """Test that fingerprints with different endpoints are not equal."""
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("GET", "/api/other", "abc123")

        assert fp1 != fp2
        assert hash(fp1) != hash(fp2)

    def test_fingerprint_inequality_method(self):
        """Test that fingerprints with different methods are not equal."""
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("POST", "/api/test", "abc123")

        assert fp1 != fp2
        assert hash(fp1) != hash(fp2)

    def test_fingerprint_inequality_params(self):
        """Test that fingerprints with different params are not equal."""
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("GET", "/api/test", "def456")

        assert fp1 != fp2
        assert hash(fp1) != hash(fp2)

    def test_fingerprint_hashable_dict_key(self):
        """Test that fingerprints can be used as dict keys."""
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("GET", "/api/test", "abc123")
        fp3 = RequestFingerprint("POST", "/api/test", "abc123")

        data: Dict[RequestFingerprint, int] = {fp1: 1, fp3: 2}

        assert data[fp1] == 1
        assert data[fp2] == 1  # Same as fp1
        assert data[fp3] == 2

    def test_fingerprint_equality_with_non_fingerprint(self):
        """Test that fingerprint comparison with non-fingerprint returns False."""
        fp = RequestFingerprint("GET", "/api/test", "abc123")

        assert fp != "not a fingerprint"
        assert fp != 123
        assert fp != None


class TestCreateFingerprint:
    """Tests for create_fingerprint function."""

    def _create_mock_request(
        self, method: str, path: str, query_params: Dict[str, str] = None
    ) -> Request:
        """Create a mock FastAPI request for testing.

        Args:
            method: HTTP method
            path: URL path
            query_params: Query parameters dict

        Returns:
            Mock Request object
        """
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": [],
        }

        request = Request(scope)

        # Mock URL
        class MockURL:
            def __init__(self, path):
                self.path = path

        request._url = MockURL(path)

        # Mock query params
        if query_params:
            request._query_params = QueryParams(query_params)
        else:
            request._query_params = QueryParams()

        return request

    def test_create_fingerprint_basic(self):
        """Test basic fingerprint creation."""
        request = self._create_mock_request("GET", "/api/test")
        fingerprint = create_fingerprint(request)

        assert fingerprint.endpoint == "/api/test"
        assert fingerprint.method == "GET"
        assert len(fingerprint.param_hash) == 8

    def test_create_fingerprint_with_params(self):
        """Test fingerprint creation with query parameters."""
        request = self._create_mock_request(
            "GET", "/api/test", {"page": "1", "limit": "10"}
        )
        fingerprint = create_fingerprint(request)

        assert fingerprint.endpoint == "/api/test"
        assert fingerprint.method == "GET"
        # param_hash should be deterministic
        assert len(fingerprint.param_hash) == 8

    def test_create_fingerprint_param_order_irrelevant(self):
        """Test that query param order doesn't affect fingerprint."""
        request1 = self._create_mock_request(
            "GET", "/api/test", {"page": "1", "limit": "10"}
        )
        request2 = self._create_mock_request(
            "GET", "/api/test", {"limit": "10", "page": "1"}
        )

        fp1 = create_fingerprint(request1)
        fp2 = create_fingerprint(request2)

        # Same params in different order should produce same fingerprint
        assert fp1 == fp2
        assert fp1.param_hash == fp2.param_hash

    def test_create_fingerprint_different_params(self):
        """Test that different params produce different fingerprints."""
        request1 = self._create_mock_request("GET", "/api/test", {"page": "1"})
        request2 = self._create_mock_request("GET", "/api/test", {"page": "2"})

        fp1 = create_fingerprint(request1)
        fp2 = create_fingerprint(request2)

        assert fp1 != fp2
        assert fp1.param_hash != fp2.param_hash


class TestSlidingWindowTracker:
    """Tests for SlidingWindowTracker sliding window accuracy."""

    def test_tracker_initialization(self):
        """Test tracker initializes with correct defaults."""
        tracker = SlidingWindowTracker(window_seconds=10)

        assert tracker.window_seconds == 10
        assert len(tracker.requests) == 0
        assert len(tracker.blocks) == 0

    def test_add_request_single(self):
        """Test adding a single request."""
        tracker = SlidingWindowTracker(window_seconds=10)
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")

        tracker.add_request("192.168.1.1", fingerprint)

        assert len(tracker.requests["192.168.1.1"]) == 1
        record = tracker.requests["192.168.1.1"][0]
        assert record.fingerprint == fingerprint
        assert record.ip == "192.168.1.1"

    def test_add_request_multiple(self):
        """Test adding multiple requests."""
        tracker = SlidingWindowTracker(window_seconds=10)
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")

        for _ in range(5):
            tracker.add_request("192.168.1.1", fingerprint)

        assert len(tracker.requests["192.168.1.1"]) == 5

    def test_sliding_window_cleanup(self):
        """Test that old requests are cleaned from the window."""
        tracker = SlidingWindowTracker(window_seconds=1)
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")

        # Add request
        tracker.add_request("192.168.1.1", fingerprint)
        assert len(tracker.requests["192.168.1.1"]) == 1

        # Wait for window to expire
        time.sleep(1.1)

        # Add another request - should clean old one
        tracker.add_request("192.168.1.1", fingerprint)

        # Should only have the new request
        assert len(tracker.requests["192.168.1.1"]) == 1

    def test_detect_burst_threshold(self):
        """Test burst detection at exact threshold (19 OK, 20 triggers)."""
        tracker = SlidingWindowTracker(window_seconds=10)
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")

        # Add 19 requests - no burst
        for _ in range(19):
            tracker.add_request("192.168.1.1", fingerprint)

        assert not tracker.detect_burst("192.168.1.1", threshold=20)

        # 20th request - burst detected
        tracker.add_request("192.168.1.1", fingerprint)
        assert tracker.detect_burst("192.168.1.1", threshold=20)

    def test_detect_burst_different_fingerprints(self):
        """Test that 20 different endpoints don't trigger burst."""
        tracker = SlidingWindowTracker(window_seconds=10)

        # Add 20 requests to different endpoints
        for i in range(20):
            fingerprint = RequestFingerprint("GET", f"/api/page/{i}", "abc123")
            tracker.add_request("192.168.1.1", fingerprint)

        # Should NOT detect burst (all different fingerprints)
        assert not tracker.detect_burst("192.168.1.1", threshold=20)

    def test_detect_burst_mixed_fingerprints(self):
        """Test burst detection with mixed fingerprints."""
        tracker = SlidingWindowTracker(window_seconds=10)
        fp1 = RequestFingerprint("GET", "/api/test", "abc123")
        fp2 = RequestFingerprint("GET", "/api/other", "abc123")

        # Add 10 of each fingerprint (20 total)
        for _ in range(10):
            tracker.add_request("192.168.1.1", fp1)
            tracker.add_request("192.168.1.1", fp2)

        # Should NOT detect burst (neither fingerprint exceeds threshold alone)
        assert not tracker.detect_burst("192.168.1.1", threshold=20)

    def test_detect_burst_empty_ip(self):
        """Test burst detection for IP with no requests."""
        tracker = SlidingWindowTracker(window_seconds=10)

        assert not tracker.detect_burst("192.168.1.1", threshold=20)

    def test_block_ip_creates_block(self):
        """Test blocking an IP address."""
        tracker = SlidingWindowTracker(window_seconds=10)

        tracker.block_ip("192.168.1.1", duration=10)

        assert tracker.is_blocked("192.168.1.1")

    def test_block_expiration(self):
        """Test that blocks expire after duration (QuickReset)."""
        tracker = SlidingWindowTracker(window_seconds=10)

        # Block for 1 second
        tracker.block_ip("192.168.1.1", duration=1)
        assert tracker.is_blocked("192.168.1.1")

        # Wait for expiration
        time.sleep(1.1)

        # Block should be cleared
        assert not tracker.is_blocked("192.168.1.1")
        # Block should be cleaned from dict
        assert "192.168.1.1" not in tracker.blocks

    def test_is_blocked_non_blocked_ip(self):
        """Test checking non-blocked IP."""
        tracker = SlidingWindowTracker(window_seconds=10)

        assert not tracker.is_blocked("192.168.1.1")

    def test_per_ip_isolation(self):
        """Test that different IPs are tracked independently."""
        tracker = SlidingWindowTracker(window_seconds=10)
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")

        # Add 20 requests from IP1
        for _ in range(20):
            tracker.add_request("192.168.1.1", fingerprint)

        # IP1 should detect burst
        assert tracker.detect_burst("192.168.1.1", threshold=20)

        # IP2 should not detect burst (no requests)
        assert not tracker.detect_burst("192.168.1.2", threshold=20)

    def test_block_per_ip_isolation(self):
        """Test that blocking one IP doesn't affect others."""
        tracker = SlidingWindowTracker(window_seconds=10)

        # Block IP1
        tracker.block_ip("192.168.1.1", duration=10)

        assert tracker.is_blocked("192.168.1.1")
        assert not tracker.is_blocked("192.168.1.2")


class TestRequestRecord:
    """Tests for RequestRecord dataclass."""

    def test_request_record_creation(self):
        """Test creating a request record."""
        fingerprint = RequestFingerprint("GET", "/api/test", "abc123")
        now = time.time()

        record = RequestRecord(
            timestamp=now,
            fingerprint=fingerprint,
            ip="192.168.1.1",
        )

        assert record.timestamp == now
        assert record.fingerprint == fingerprint
        assert record.ip == "192.168.1.1"
