#!/usr/bin/env python3
"""Demo script showing score decay in action.

This script demonstrates how the ScoreDecay system applies time-based
decay to community scores while preserving user ratings.
"""

from datetime import datetime, timedelta, timezone

from skillmeat.core.scoring import (
    ScoreAggregator,
    ScoreDecay,
    ScoreSource,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def main():
    """Run score decay demonstration."""
    print_section("Score Decay Demonstration")
    print("Showing how time-based decay affects community scores\n")

    # Initialize components
    decay = ScoreDecay()
    aggregator = ScoreAggregator()
    now = datetime.now(timezone.utc)

    # Example 1: Fresh vs Stale GitHub Stars
    print_section("Example 1: Fresh vs Stale GitHub Stars")

    fresh_stars = ScoreSource("github_stars", 80.0, 0.25, now, 150)
    stale_stars = ScoreSource("github_stars", 80.0, 0.25, now - timedelta(days=365), 150)

    fresh_result = decay.apply_decay(fresh_stars.score, fresh_stars.last_updated)
    stale_result = decay.apply_decay(stale_stars.score, stale_stars.last_updated)

    print(f"\nFresh stars (0 months old):")
    print(f"  Original: {fresh_result.original_score:.1f}")
    print(f"  Decayed:  {fresh_result.decayed_score:.1f} (factor: {fresh_result.decay_factor:.3f})")

    print(f"\nStale stars (12 months old):")
    print(f"  Original: {stale_result.original_score:.1f}")
    print(f"  Decayed:  {stale_result.decayed_score:.1f} (factor: {stale_result.decay_factor:.3f})")
    print(f"  Loss:     {stale_result.original_score - stale_result.decayed_score:.1f} points")

    # Example 2: User Rating Never Decays
    print_section("Example 2: User Rating Never Decays")

    old_user_rating = ScoreSource("user_rating", 90.0, 0.4, now - timedelta(days=365), 5)

    # Using aggregate_with_decay
    sources = [old_user_rating]
    result_with_decay = aggregator.aggregate_with_decay(sources, decay)
    result_no_decay = aggregator.aggregate(sources)

    print(f"\nUser rating (12 months old):")
    print(f"  Original score:     {old_user_rating.score:.1f}")
    print(f"  With decay system:  {result_with_decay.final_score:.1f}")
    print(f"  Without decay:      {result_no_decay.final_score:.1f}")
    print(f"  Difference:         {abs(result_with_decay.final_score - result_no_decay.final_score):.1f} (no decay applied)")

    # Example 3: Mixed Sources
    print_section("Example 3: Mixed Sources with Different Ages")

    sources = [
        ScoreSource("github_stars", 85.0, 0.25, now - timedelta(days=180), 200),  # 6 months old
        ScoreSource("registry", 75.0, 0.2, now - timedelta(days=90), 100),  # 3 months old
        ScoreSource("user_rating", 90.0, 0.4, now, 8),  # Fresh
        ScoreSource("maintenance", 70.0, 0.15, now - timedelta(days=365), 1),  # Old (doesn't decay)
    ]

    result_with_decay = aggregator.aggregate_with_decay(sources, decay)
    result_no_decay = aggregator.aggregate(sources)

    print("\nSource breakdown:")
    for source in sources:
        age_days = (now - source.last_updated).total_seconds() / 86400
        months_old = age_days / 30.0

        if source.source_name in {"github_stars", "registry", "community"}:
            decayed = decay.apply_decay(source.score, source.last_updated)
            print(f"  {source.source_name:15s} ({months_old:4.1f} months): {source.score:5.1f} → {decayed.decayed_score:5.1f}")
        else:
            print(f"  {source.source_name:15s} ({months_old:4.1f} months): {source.score:5.1f} (no decay)")

    print(f"\nAggregated scores:")
    print(f"  With decay:    {result_with_decay.final_score:.1f} (confidence: {result_with_decay.confidence:.2f})")
    print(f"  Without decay: {result_no_decay.final_score:.1f} (confidence: {result_no_decay.confidence:.2f})")
    print(f"  Impact:        -{abs(result_no_decay.final_score - result_with_decay.final_score):.1f} points")

    # Example 4: Decay Progression Over Time
    print_section("Example 4: Decay Progression Over Time")

    original_score = 80.0

    print(f"\nOriginal score: {original_score:.1f}")
    print("Decay progression:")

    for months in [0, 3, 6, 12, 18, 24]:
        days = months * 30
        timestamp = now - timedelta(days=days)
        result = decay.apply_decay(original_score, timestamp)

        print(f"  {months:2d} months: {result.decayed_score:5.1f} "
              f"(factor: {result.decay_factor:.3f}, "
              f"-{result.original_score - result.decayed_score:4.1f} points)")

    # Example 5: Should Refresh Check
    print_section("Example 5: Refresh Recommendations")

    test_cases = [
        (30, "1 month old"),
        (60, "2 months old"),
        (90, "3 months old"),
        (180, "6 months old"),
    ]

    print("\nRefresh recommendations (threshold: 60 days):")
    for days, label in test_cases:
        timestamp = now - timedelta(days=days)
        should_refresh = decay.should_refresh(timestamp, threshold_days=60)
        status = "✓ Refresh recommended" if should_refresh else "✗ Fresh enough"
        print(f"  {label:15s}: {status}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
