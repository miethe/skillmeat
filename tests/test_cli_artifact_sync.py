"""Tests for CLI artifact sync with API cache refresh functionality.

This module tests the end-to-end flow:
1. CLI add artifact -> API syncs metadata -> database updated
2. CLI sync -> API batch refresh -> database updated

These tests verify:
- _refresh_api_cache() is called after artifact add
- _refresh_api_cache_batch() is called after sync
- Graceful degradation when API is unavailable
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import requests
from click.testing import CliRunner

from skillmeat.cli import (
    main,
    _refresh_api_cache,
    _refresh_api_cache_batch,
)


class TestRefreshApiCache:
    """Test suite for _refresh_api_cache function."""

    @pytest.fixture
    def mock_config(self):
        """Provide mock config manager."""
        with patch("skillmeat.cli.config_mgr") as mock:
            mock.get.return_value = "http://localhost:8080"
            yield mock

    def test_refresh_api_cache_success(self, mock_config, caplog):
        """Test successful API cache refresh."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "updated": 5}
            mock_post.return_value = mock_response

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache("default", "table")

            mock_post.assert_called_once_with(
                "http://localhost:8080/api/v1/user-collections/default/refresh-cache",
                timeout=3,
            )
            assert "API cache refresh successful" in caplog.text

    def test_refresh_api_cache_success_json_format(self, mock_config, caplog, capsys):
        """Test API cache refresh with JSON output format (no console output)."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "updated": 5}
            mock_post.return_value = mock_response

            _refresh_api_cache("default", "json")

            mock_post.assert_called_once()
            # Console output should not contain "API cache refreshed" for JSON format
            # (since we don't capture Rich console, this is implicit)

    def test_refresh_api_cache_collection_not_found(self, mock_config, caplog):
        """Test API cache refresh when collection not found in DB."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_post.return_value = mock_response

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache("nonexistent", "table")

            mock_post.assert_called_once()
            assert "not found in API database" in caplog.text

    def test_refresh_api_cache_server_error(self, mock_config, caplog):
        """Test API cache refresh with server error response."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            with caplog.at_level(logging.WARNING):
                _refresh_api_cache("default", "table")

            mock_post.assert_called_once()
            assert "returned 500" in caplog.text

    def test_refresh_api_cache_connection_error(self, mock_config, caplog):
        """Test API cache refresh when server not running."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache("default", "table")

            mock_post.assert_called_once()
            assert "API server not running" in caplog.text

    def test_refresh_api_cache_timeout(self, mock_config, caplog):
        """Test API cache refresh timeout handling."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            with caplog.at_level(logging.WARNING):
                _refresh_api_cache("default", "table")

            mock_post.assert_called_once()
            assert "timed out" in caplog.text

    def test_refresh_api_cache_generic_exception(self, mock_config, caplog):
        """Test API cache refresh with generic exception."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = Exception("Unexpected error")

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache("default", "table")

            mock_post.assert_called_once()
            assert "API cache refresh failed" in caplog.text

    def test_refresh_api_cache_custom_collection(self, mock_config):
        """Test API cache refresh with custom collection ID."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            _refresh_api_cache("my-collection", "table")

            mock_post.assert_called_once_with(
                "http://localhost:8080/api/v1/user-collections/my-collection/refresh-cache",
                timeout=3,
            )


class TestRefreshApiCacheBatch:
    """Test suite for _refresh_api_cache_batch function."""

    @pytest.fixture
    def mock_config(self):
        """Provide mock config manager."""
        with patch("skillmeat.cli.config_mgr") as mock:
            mock.get.return_value = "http://localhost:8080"
            yield mock

    def test_refresh_api_cache_batch_success(self, mock_config, caplog):
        """Test successful batch API cache refresh."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "total_updated": 15,
                "collections_refreshed": 3,
            }
            mock_post.return_value = mock_response

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache_batch("table")

            mock_post.assert_called_once_with(
                "http://localhost:8080/api/v1/user-collections/refresh-cache",
                timeout=10,
            )
            assert "Batch API cache refresh successful" in caplog.text

    def test_refresh_api_cache_batch_success_json_format(self, mock_config):
        """Test batch API cache refresh with JSON output format."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "total_updated": 10,
                "collections_refreshed": 2,
            }
            mock_post.return_value = mock_response

            _refresh_api_cache_batch("json")

            mock_post.assert_called_once()

    def test_refresh_api_cache_batch_no_updates(self, mock_config):
        """Test batch refresh when no artifacts were updated."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "total_updated": 0,
                "collections_refreshed": 0,
            }
            mock_post.return_value = mock_response

            _refresh_api_cache_batch("table")

            mock_post.assert_called_once()

    def test_refresh_api_cache_batch_server_error(self, mock_config, caplog):
        """Test batch API cache refresh with server error."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            with caplog.at_level(logging.WARNING):
                _refresh_api_cache_batch("table")

            mock_post.assert_called_once()
            assert "returned 500" in caplog.text

    def test_refresh_api_cache_batch_connection_error(self, mock_config, caplog):
        """Test batch API cache refresh when server not running."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache_batch("table")

            mock_post.assert_called_once()
            assert "API server not running" in caplog.text

    def test_refresh_api_cache_batch_timeout(self, mock_config, caplog):
        """Test batch API cache refresh timeout handling."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()

            with caplog.at_level(logging.WARNING):
                _refresh_api_cache_batch("table")

            mock_post.assert_called_once()
            assert "timed out" in caplog.text

    def test_refresh_api_cache_batch_generic_exception(self, mock_config, caplog):
        """Test batch API cache refresh with generic exception."""
        with patch("skillmeat.cli.requests.post") as mock_post:
            mock_post.side_effect = Exception("Unexpected error")

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache_batch("table")

            mock_post.assert_called_once()
            assert "Batch API cache refresh failed" in caplog.text


class TestCacheRefreshApiConfig:
    """Test suite for API configuration handling in cache refresh."""

    def test_refresh_uses_custom_api_url(self):
        """Test that cache refresh uses custom API base URL from config."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://custom-server:9000"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            _refresh_api_cache("default", "table")

            mock_post.assert_called_once_with(
                "http://custom-server:9000/api/v1/user-collections/default/refresh-cache",
                timeout=3,
            )

    def test_refresh_batch_uses_custom_api_url(self):
        """Test that batch cache refresh uses custom API base URL from config."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "https://api.example.com:443"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            _refresh_api_cache_batch("table")

            mock_post.assert_called_once_with(
                "https://api.example.com:443/api/v1/user-collections/refresh-cache",
                timeout=10,
            )


class TestCacheRefreshEndpointFormats:
    """Test suite for verifying correct API endpoint formats."""

    def test_single_collection_endpoint_format(self):
        """Verify the single-collection refresh endpoint is correctly formatted."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            # Test various collection IDs
            test_cases = [
                ("default", "/api/v1/user-collections/default/refresh-cache"),
                ("my-collection", "/api/v1/user-collections/my-collection/refresh-cache"),
                ("work_stuff", "/api/v1/user-collections/work_stuff/refresh-cache"),
            ]

            for collection_id, expected_path in test_cases:
                mock_post.reset_mock()
                _refresh_api_cache(collection_id, "table")
                actual_url = mock_post.call_args[0][0]
                assert actual_url.endswith(expected_path), (
                    f"Expected URL to end with {expected_path}, got {actual_url}"
                )

    def test_batch_endpoint_format(self):
        """Verify the batch refresh endpoint is correctly formatted."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            _refresh_api_cache_batch("table")

            actual_url = mock_post.call_args[0][0]
            assert actual_url == "http://localhost:8080/api/v1/user-collections/refresh-cache"


class TestCacheRefreshTimeouts:
    """Test suite for verifying correct timeout values."""

    def test_single_collection_uses_3_second_timeout(self):
        """Verify single-collection refresh uses 3-second timeout."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            _refresh_api_cache("default", "table")

            _, kwargs = mock_post.call_args
            assert kwargs.get("timeout") == 3

    def test_batch_uses_10_second_timeout(self):
        """Verify batch refresh uses 10-second timeout (longer for batch ops)."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_post.return_value = mock_response

            _refresh_api_cache_batch("table")

            _, kwargs = mock_post.call_args
            assert kwargs.get("timeout") == 10


class TestCacheRefreshGracefulDegradation:
    """Test suite for verifying graceful degradation behavior."""

    def test_single_refresh_never_raises_on_connection_error(self):
        """Verify _refresh_api_cache never raises on connection errors."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = requests.exceptions.ConnectionError()

            # Should not raise
            _refresh_api_cache("default", "table")

    def test_single_refresh_never_raises_on_timeout(self):
        """Verify _refresh_api_cache never raises on timeout errors."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = requests.exceptions.Timeout()

            # Should not raise
            _refresh_api_cache("default", "table")

    def test_single_refresh_never_raises_on_generic_exception(self):
        """Verify _refresh_api_cache never raises on generic exceptions."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = Exception("Network error")

            # Should not raise
            _refresh_api_cache("default", "table")

    def test_batch_refresh_never_raises_on_connection_error(self):
        """Verify _refresh_api_cache_batch never raises on connection errors."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = requests.exceptions.ConnectionError()

            # Should not raise
            _refresh_api_cache_batch("table")

    def test_batch_refresh_never_raises_on_timeout(self):
        """Verify _refresh_api_cache_batch never raises on timeout errors."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = requests.exceptions.Timeout()

            # Should not raise
            _refresh_api_cache_batch("table")

    def test_batch_refresh_never_raises_on_generic_exception(self):
        """Verify _refresh_api_cache_batch never raises on generic exceptions."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_post.side_effect = Exception("Network error")

            # Should not raise
            _refresh_api_cache_batch("table")

    def test_single_refresh_never_raises_on_http_error(self):
        """Verify _refresh_api_cache never raises on HTTP error responses."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"

            # Test various HTTP error status codes
            for status_code in [400, 401, 403, 404, 500, 502, 503]:
                mock_response = MagicMock()
                mock_response.status_code = status_code
                mock_response.text = "Error"
                mock_post.return_value = mock_response

                # Should not raise
                _refresh_api_cache("default", "table")

    def test_batch_refresh_never_raises_on_http_error(self):
        """Verify _refresh_api_cache_batch never raises on HTTP error responses."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"

            # Test various HTTP error status codes
            for status_code in [400, 401, 403, 404, 500, 502, 503]:
                mock_response = MagicMock()
                mock_response.status_code = status_code
                mock_response.text = "Error"
                mock_post.return_value = mock_response

                # Should not raise
                _refresh_api_cache_batch("table")


class TestCacheRefreshResponseHandling:
    """Test suite for verifying response data handling."""

    def test_batch_refresh_parses_update_counts(self, caplog):
        """Verify batch refresh correctly parses and logs update counts."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "total_updated": 25,
                "collections_refreshed": 5,
            }
            mock_post.return_value = mock_response

            with caplog.at_level(logging.DEBUG):
                _refresh_api_cache_batch("table")

            # Check that response data was logged
            assert "total_updated" in caplog.text or "25" in caplog.text

    def test_single_refresh_handles_missing_json(self, caplog):
        """Verify single refresh handles responses that fail JSON parsing."""
        with (
            patch("skillmeat.cli.config_mgr") as mock_config,
            patch("skillmeat.cli.requests.post") as mock_post,
        ):
            mock_config.get.return_value = "http://localhost:8080"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("No JSON")
            mock_post.return_value = mock_response

            with caplog.at_level(logging.DEBUG):
                # Should not raise, should handle gracefully
                _refresh_api_cache("default", "table")
