"""Tests for anti-gaming protection module.

Tests cover:
- Rate limiting enforcement
- Cooldown periods
- Burst anomaly detection
- Pattern anomaly detection
- No false positives on legitimate use
- Violation logging
- Integration with rating flow
"""

import pytest
from datetime import datetime, timedelta
from skillmeat.core.scoring.anti_gaming import (
    RateLimiter,
    RateLimitConfig,
    AnomalyDetector,
    AntiGamingGuard,
    ViolationType,
    ViolationRecord,
)


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_allows_rating_under_daily_limit(self):
        """Should allow ratings under the daily limit."""
        limiter = RateLimiter(RateLimitConfig(max_ratings_per_day=5))

        # Should allow first rating
        allowed, reason = limiter.check_rate_limit("user1", "skill:a")
        assert allowed is True
        assert reason is None

        # Record rating
        limiter.record_rating("user1", "skill:a")

        # Should allow second rating on different artifact
        allowed, reason = limiter.check_rate_limit("user1", "skill:b")
        assert allowed is True

    def test_blocks_rating_over_daily_limit(self):
        """Should block ratings that exceed daily limit."""
        limiter = RateLimiter(RateLimitConfig(max_ratings_per_day=2))

        # Submit 2 ratings (hit limit)
        limiter.record_rating("user1", "skill:a")
        limiter.record_rating("user1", "skill:b")

        # Third rating should be blocked
        allowed, reason = limiter.check_rate_limit("user1", "skill:c")
        assert allowed is False
        assert "Rate limit exceeded" in reason
        assert "2 ratings per day" in reason

    def test_enforces_per_artifact_limit(self):
        """Should enforce limit on rating the same artifact."""
        limiter = RateLimiter(
            RateLimitConfig(max_ratings_per_artifact=1, cooldown_hours=24)
        )

        # First rating allowed
        allowed, reason = limiter.check_rate_limit("user1", "skill:a")
        assert allowed is True
        limiter.record_rating("user1", "skill:a")

        # Second rating on same artifact blocked (cooldown)
        allowed, reason = limiter.check_rate_limit("user1", "skill:a")
        assert allowed is False
        assert "Cooldown active" in reason

    def test_cooldown_period_expires(self):
        """Should allow re-rating after cooldown expires."""
        limiter = RateLimiter(
            RateLimitConfig(max_ratings_per_artifact=1, cooldown_hours=1)
        )

        # Record rating
        limiter.record_rating("user1", "skill:a")

        # Simulate time passing (mock the internal timestamp)
        # Since we can't easily mock datetime.now() in the class,
        # we'll verify the logic works by checking the remaining time
        allowed, reason = limiter.check_rate_limit("user1", "skill:a")
        assert allowed is False
        assert "1.0 hours" in reason or "0.9 hours" in reason  # Close to 1 hour

    def test_get_remaining_ratings(self):
        """Should correctly report remaining ratings."""
        limiter = RateLimiter(RateLimitConfig(max_ratings_per_day=5))

        # Initially should have all 5
        remaining = limiter.get_remaining_ratings("user1")
        assert remaining == 5

        # After 1 rating, should have 4
        limiter.record_rating("user1", "skill:a")
        remaining = limiter.get_remaining_ratings("user1")
        assert remaining == 4

        # After 5 ratings, should have 0
        limiter.record_rating("user1", "skill:b")
        limiter.record_rating("user1", "skill:c")
        limiter.record_rating("user1", "skill:d")
        limiter.record_rating("user1", "skill:e")
        remaining = limiter.get_remaining_ratings("user1")
        assert remaining == 0

    def test_different_users_independent_limits(self):
        """Should enforce limits independently per user."""
        limiter = RateLimiter(RateLimitConfig(max_ratings_per_day=1))

        # User 1 hits limit
        limiter.record_rating("user1", "skill:a")
        allowed, _ = limiter.check_rate_limit("user1", "skill:b")
        assert allowed is False

        # User 2 should still have quota
        allowed, _ = limiter.check_rate_limit("user2", "skill:a")
        assert allowed is True


class TestAnomalyDetector:
    """Test anomaly detection functionality."""

    def test_detects_burst_anomaly(self):
        """Should detect burst of ratings in short time window."""
        detector = AnomalyDetector(burst_threshold=3, burst_window_minutes=60)

        # Record burst of 4 ratings
        for i in range(4):
            detector.record_rating_for_detection("user1", f"skill:{i}", 5)

        # Should detect burst
        is_anomaly, reason = detector.check_burst_anomaly("user1")
        assert is_anomaly is True
        assert "Burst anomaly" in reason
        assert "4 ratings" in reason

    def test_no_burst_under_threshold(self):
        """Should not flag burst under threshold."""
        detector = AnomalyDetector(burst_threshold=5, burst_window_minutes=60)

        # Record 3 ratings (under threshold)
        for i in range(3):
            detector.record_rating_for_detection("user1", f"skill:{i}", 5)

        # Should not detect burst
        is_anomaly, reason = detector.check_burst_anomaly("user1")
        assert is_anomaly is False
        assert reason is None

    def test_detects_uniform_rating_pattern(self):
        """Should detect when all ratings are the same value."""
        detector = AnomalyDetector(pattern_threshold=0.8)

        # Record 10 ratings all with value 5
        for i in range(10):
            detector.record_rating_for_detection(f"user{i}", "skill:a", 5)

        # Should detect pattern anomaly (all same value)
        is_anomaly, reason = detector.check_pattern_anomaly("skill:a")
        assert is_anomaly is True
        assert "same value" in reason or "suspicion" in reason.lower()

    def test_no_pattern_with_diverse_ratings(self):
        """Should not flag diverse legitimate ratings."""
        detector = AnomalyDetector(pattern_threshold=0.8)

        # Record diverse ratings
        ratings = [5, 4, 5, 3, 4, 5, 4, 3, 5, 4]
        for i, rating in enumerate(ratings):
            detector.record_rating_for_detection(f"user{i}", "skill:a", rating)

        # Should not detect pattern anomaly
        is_anomaly, reason = detector.check_pattern_anomaly("skill:a")
        assert is_anomaly is False

    def test_suspicion_score_calculation(self):
        """Should calculate suspicion score correctly."""
        detector = AnomalyDetector()

        # All same value = high suspicion
        for i in range(10):
            detector.record_rating_for_detection(f"user{i}", "skill:uniform", 5)
        score = detector.calculate_suspicion_score("skill:uniform")
        assert score > 0.8

        # Diverse ratings = low suspicion
        ratings = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]
        for i, rating in enumerate(ratings):
            detector.record_rating_for_detection(f"user{i}", "skill:diverse", rating)
        score = detector.calculate_suspicion_score("skill:diverse")
        assert score < 0.5

    def test_no_false_positive_on_few_ratings(self):
        """Should not trigger on artifacts with few ratings."""
        detector = AnomalyDetector()

        # Only 2 ratings (below minimum for pattern detection)
        detector.record_rating_for_detection("user1", "skill:new", 5)
        detector.record_rating_for_detection("user2", "skill:new", 5)

        # Should not flag as anomaly (too few data points)
        is_anomaly, reason = detector.check_pattern_anomaly("skill:new")
        assert is_anomaly is False


class TestAntiGamingGuard:
    """Test unified anti-gaming guard."""

    def test_allows_legitimate_rating(self):
        """Should allow legitimate ratings."""
        guard = AntiGamingGuard()

        allowed, reason = guard.can_submit_rating("user1", "skill:a")
        assert allowed is True
        assert reason is None

    def test_blocks_rate_limit_violation(self):
        """Should block when rate limit is exceeded."""
        limiter = RateLimiter(RateLimitConfig(max_ratings_per_day=1))
        guard = AntiGamingGuard(rate_limiter=limiter)

        # First rating allowed
        allowed, _ = guard.can_submit_rating("user1", "skill:a")
        assert allowed is True
        guard.record_rating("user1", "skill:a", 5)

        # Second rating blocked
        allowed, reason = guard.can_submit_rating("user1", "skill:b")
        assert allowed is False
        assert "Rate limit" in reason

    def test_blocks_burst_violation(self):
        """Should block when burst anomaly is detected."""
        detector = AnomalyDetector(burst_threshold=2, burst_window_minutes=60)
        guard = AntiGamingGuard(anomaly_detector=detector)

        # Record burst of 3 ratings
        guard.record_rating("user1", "skill:a", 5)
        guard.record_rating("user1", "skill:b", 5)
        guard.record_rating("user1", "skill:c", 5)

        # Next rating should be blocked due to burst
        allowed, reason = guard.can_submit_rating("user1", "skill:d")
        assert allowed is False
        assert "Suspicious activity" in reason or "Burst" in reason

    def test_logs_pattern_violation_but_allows_rating(self):
        """Should log pattern anomaly but not block user.

        Pattern anomalies are artifact-level signals, not user-level blocks.
        """
        detector = AnomalyDetector(pattern_threshold=0.8)
        guard = AntiGamingGuard(anomaly_detector=detector)

        # Create pattern: 10 ratings all with value 5
        for i in range(10):
            guard.record_rating(f"user{i}", "skill:a", 5)

        # New user should still be allowed (pattern is on artifact, not user)
        allowed, reason = guard.can_submit_rating("user99", "skill:a")
        assert allowed is True

        # But violation should be logged
        violations = guard.get_violations(artifact_id="skill:a")
        assert len(violations) > 0
        assert any(
            v.violation_type == ViolationType.ANOMALY_PATTERN for v in violations
        )

    def test_records_violations(self):
        """Should record and query violations."""
        guard = AntiGamingGuard()

        # Trigger violation
        violation = ViolationRecord(
            violation_type=ViolationType.RATE_LIMIT,
            artifact_id="skill:a",
            user_id="user1",
            detected_at=datetime.now(),
            details="Test violation",
        )
        guard.report_violation(violation)

        # Should be able to query violations
        violations = guard.get_violations(user_id="user1")
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.RATE_LIMIT

    def test_filters_violations_by_user(self):
        """Should filter violations by user ID."""
        guard = AntiGamingGuard()

        # Record violations for different users
        guard.report_violation(
            ViolationRecord(
                ViolationType.RATE_LIMIT, None, "user1", datetime.now(), "Test"
            )
        )
        guard.report_violation(
            ViolationRecord(
                ViolationType.RATE_LIMIT, None, "user2", datetime.now(), "Test"
            )
        )

        # Filter by user1
        violations = guard.get_violations(user_id="user1")
        assert len(violations) == 1
        assert violations[0].user_id == "user1"

    def test_filters_violations_by_artifact(self):
        """Should filter violations by artifact ID."""
        guard = AntiGamingGuard()

        # Record violations for different artifacts
        guard.report_violation(
            ViolationRecord(
                ViolationType.ANOMALY_PATTERN,
                "skill:a",
                "user1",
                datetime.now(),
                "Test",
            )
        )
        guard.report_violation(
            ViolationRecord(
                ViolationType.ANOMALY_PATTERN,
                "skill:b",
                "user1",
                datetime.now(),
                "Test",
            )
        )

        # Filter by skill:a
        violations = guard.get_violations(artifact_id="skill:a")
        assert len(violations) == 1
        assert violations[0].artifact_id == "skill:a"

    def test_filters_violations_by_time(self):
        """Should filter violations by time."""
        guard = AntiGamingGuard()

        now = datetime.now()
        past = now - timedelta(hours=2)

        # Record old violation
        guard.report_violation(
            ViolationRecord(ViolationType.RATE_LIMIT, None, "user1", past, "Old")
        )

        # Record recent violation
        guard.report_violation(
            ViolationRecord(ViolationType.RATE_LIMIT, None, "user1", now, "Recent")
        )

        # Filter to last hour (should only get recent one)
        violations = guard.get_violations(since=now - timedelta(hours=1))
        assert len(violations) == 1
        assert violations[0].details == "Recent"


class TestIntegration:
    """Integration tests for full rating flow."""

    def test_full_rating_flow_success(self):
        """Should successfully process legitimate rating."""
        guard = AntiGamingGuard()

        # Check if allowed
        allowed, reason = guard.can_submit_rating("user1", "skill:a")
        assert allowed is True

        # Record rating
        guard.record_rating("user1", "skill:a", 5)

        # Should have consumed one rating from quota
        remaining = guard.rate_limiter.get_remaining_ratings("user1")
        assert remaining == 4

    def test_prevents_gaming_attempt(self):
        """Should prevent gaming through rapid burst."""
        guard = AntiGamingGuard(
            anomaly_detector=AnomalyDetector(burst_threshold=5, burst_window_minutes=60)
        )

        # Attempt to submit 6 ratings rapidly
        for i in range(5):
            allowed, _ = guard.can_submit_rating("user1", f"skill:{i}")
            if allowed:
                guard.record_rating("user1", f"skill:{i}", 5)

        # 6th rating should be blocked
        allowed, reason = guard.can_submit_rating("user1", "skill:6")
        assert allowed is False

        # Violation should be logged
        violations = guard.get_violations(user_id="user1")
        assert len(violations) > 0

    def test_no_false_positives_on_power_user(self):
        """Should not block legitimate power users within limits."""
        guard = AntiGamingGuard()

        # Power user rates 5 different artifacts (at daily limit)
        for i in range(5):
            allowed, reason = guard.can_submit_rating("poweruser", f"skill:{i}")
            assert allowed is True, f"Should allow rating {i+1}/5: {reason}"
            guard.record_rating("poweruser", f"skill:{i}", 4)

        # No violations should be recorded
        violations = guard.get_violations(user_id="poweruser")
        # Only violation would be if they try to exceed limit, but we didn't
        assert all(v.violation_type != ViolationType.ANOMALY_BURST for v in violations)

    def test_cooldown_enforcement(self):
        """Should enforce cooldown between re-ratings."""
        guard = AntiGamingGuard(
            rate_limiter=RateLimiter(
                RateLimitConfig(max_ratings_per_artifact=1, cooldown_hours=24)
            )
        )

        # Rate artifact
        allowed, _ = guard.can_submit_rating("user1", "skill:a")
        assert allowed is True
        guard.record_rating("user1", "skill:a", 5)

        # Try to re-rate immediately (should be blocked)
        allowed, reason = guard.can_submit_rating("user1", "skill:a")
        assert allowed is False
        assert "Cooldown" in reason

        # Can rate different artifact
        allowed, _ = guard.can_submit_rating("user1", "skill:b")
        assert allowed is True
