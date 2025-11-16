"""Shared fixtures for integration tests.

Provides fixtures for:
- Analytics workspace with collection + analytics DB
- Populated analytics databases with realistic test data
- Large datasets for performance testing
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pytest

from skillmeat.config import ConfigManager
from skillmeat.core.analytics import EventTracker
from skillmeat.core.usage_reports import UsageReportManager
from skillmeat.storage.analytics import AnalyticsDB


@pytest.fixture
def analytics_workspace(tmp_path, monkeypatch):
    """Create a complete workspace with collection and analytics DB.

    Sets up:
    - Temporary home directory
    - SkillMeat collection directory
    - Analytics database
    - Config file with analytics enabled

    Returns:
        Dict with paths and initialized components:
        - home: Path to temp home
        - collection: Path to collection directory
        - analytics_db_path: Path to analytics database
        - config: ConfigManager instance
        - db: AnalyticsDB instance
        - tracker: EventTracker instance
    """
    # Create temp home
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))

    # Create .skillmeat directory structure
    skillmeat_dir = home_dir / ".skillmeat"
    skillmeat_dir.mkdir(parents=True, exist_ok=True)

    # Create collections directory
    collections_dir = skillmeat_dir / "collections"
    collections_dir.mkdir(parents=True, exist_ok=True)

    default_collection = collections_dir / "default"
    default_collection.mkdir(parents=True, exist_ok=True)

    # Create analytics DB path
    analytics_db_path = skillmeat_dir / "analytics.db"

    # Create config file with analytics enabled
    config_path = skillmeat_dir / "config.toml"
    config_content = """
[analytics]
enabled = true
retention_days = 90

[collections]
dir = "{collections_dir}"
default = "default"
""".format(
        collections_dir=str(collections_dir)
    )
    config_path.write_text(config_content)

    # Initialize components
    config = ConfigManager(config_dir=skillmeat_dir)
    db = AnalyticsDB(db_path=analytics_db_path)
    tracker = EventTracker(config_manager=config)

    return {
        "home": home_dir,
        "skillmeat_dir": skillmeat_dir,
        "collection": default_collection,
        "collections_dir": collections_dir,
        "analytics_db_path": analytics_db_path,
        "config": config,
        "db": db,
        "tracker": tracker,
    }


@pytest.fixture
def populated_analytics_db(analytics_workspace):
    """Create analytics DB with 100+ realistic events.

    Generates events spanning 30 days with varied patterns:
    - Multiple artifacts (skills, commands, agents)
    - Different event types (deploy, update, sync, search, remove)
    - Temporal patterns (some heavily used, some idle)
    - Different collections

    Returns:
        Dict with workspace and event metadata:
        - All analytics_workspace keys
        - events: List of generated events
        - artifact_names: List of artifact names
        - start_date: Earliest event timestamp
        - end_date: Latest event timestamp
    """
    workspace = analytics_workspace
    db = workspace["db"]

    # Define test artifacts
    artifacts = [
        {"name": "canvas", "type": "skill", "popularity": "high"},
        {"name": "python-expert", "type": "skill", "popularity": "high"},
        {"name": "git-helper", "type": "command", "popularity": "medium"},
        {"name": "code-review", "type": "agent", "popularity": "medium"},
        {"name": "legacy-tool", "type": "skill", "popularity": "low"},
        {"name": "deprecated-cmd", "type": "command", "popularity": "unused"},
    ]

    # Generate events over 30 days
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    events = []

    for artifact in artifacts:
        if artifact["popularity"] == "high":
            # Deploy + frequent updates and syncs
            event_count = 40
        elif artifact["popularity"] == "medium":
            # Deploy + moderate usage
            event_count = 15
        elif artifact["popularity"] == "low":
            # Deploy + rare usage
            event_count = 5
        else:  # unused
            # Only initial deploy, long ago
            event_count = 1

        for i in range(event_count):
            if artifact["popularity"] == "unused":
                # Old deploy event only
                timestamp = start_date.isoformat()
                event_type = "deploy"
            else:
                # Spread events across time period
                days_offset = (i / event_count) * 30
                event_time = start_date + timedelta(days=days_offset)
                timestamp = event_time.isoformat()

                # Choose event type based on position
                if i == 0:
                    event_type = "deploy"
                elif i % 5 == 0:
                    event_type = "update"
                elif i % 3 == 0:
                    event_type = "sync"
                elif i % 7 == 0:
                    event_type = "search"
                else:
                    event_type = "sync"

            metadata = {
                "version": "1.0.0",
                "source": "github",
                "timestamp": timestamp,
            }

            db.record_event(
                event_type=event_type,
                artifact_name=artifact["name"],
                artifact_type=artifact["type"],
                collection_name="default",
                project_path="/home/user/test-project",
                metadata=metadata,
            )

            events.append(
                {
                    "event_type": event_type,
                    "artifact_name": artifact["name"],
                    "artifact_type": artifact["type"],
                    "timestamp": timestamp,
                }
            )

    return {
        **workspace,
        "events": events,
        "artifact_names": [a["name"] for a in artifacts],
        "start_date": start_date,
        "end_date": end_date,
    }


@pytest.fixture
def large_analytics_db(analytics_workspace):
    """Create analytics DB with 10,000+ events for performance testing.

    Generates large dataset with:
    - 10,000 events
    - 50 unique artifacts
    - Realistic distribution across event types
    - Spans 90 days

    Returns:
        Dict with workspace and metadata:
        - All analytics_workspace keys
        - event_count: Total events generated
        - artifact_count: Number of unique artifacts
    """
    workspace = analytics_workspace
    db = workspace["db"]

    # Generate 50 artifacts
    artifact_count = 50
    artifacts = []
    for i in range(artifact_count):
        artifact_type = ["skill", "command", "agent"][i % 3]
        artifacts.append(
            {
                "name": f"artifact-{i:03d}",
                "type": artifact_type,
            }
        )

    # Generate 10,000 events
    target_events = 10000
    events_per_artifact = target_events // artifact_count

    start_date = datetime.now() - timedelta(days=90)

    for artifact in artifacts:
        for i in range(events_per_artifact):
            # Spread events across 90 days
            days_offset = (i / events_per_artifact) * 90
            event_time = start_date + timedelta(days=days_offset)
            timestamp = event_time.isoformat()

            # Event type distribution
            event_types = ["deploy", "update", "sync", "search", "remove"]
            weights = [0.1, 0.2, 0.4, 0.2, 0.1]  # Sync most common
            import random

            random.seed(i)  # Deterministic
            event_type = random.choices(event_types, weights=weights)[0]

            db.record_event(
                event_type=event_type,
                artifact_name=artifact["name"],
                artifact_type=artifact["type"],
                collection_name="default",
                project_path=f"/home/user/project-{i % 10}",
                metadata={"timestamp": timestamp},
            )

    return {
        **workspace,
        "event_count": target_events,
        "artifact_count": artifact_count,
    }


@pytest.fixture
def analytics_db_with_old_data(analytics_workspace):
    """Create analytics DB with old data for cleanup testing.

    Generates:
    - Events from 180 days ago (should be cleaned up)
    - Events from 60 days ago (should be retained)
    - Recent events (should be retained)

    Returns:
        Dict with workspace and timestamp info
    """
    workspace = analytics_workspace
    db = workspace["db"]

    now = datetime.now()

    # Old events (180 days ago)
    old_time = now - timedelta(days=180)
    for i in range(10):
        db.record_event(
            event_type="deploy",
            artifact_name=f"old-artifact-{i}",
            artifact_type="skill",
            collection_name="default",
            metadata={"timestamp": old_time.isoformat()},
        )

    # Medium-age events (60 days ago)
    medium_time = now - timedelta(days=60)
    for i in range(10):
        db.record_event(
            event_type="sync",
            artifact_name=f"medium-artifact-{i}",
            artifact_type="command",
            collection_name="default",
            metadata={"timestamp": medium_time.isoformat()},
        )

    # Recent events
    for i in range(10):
        db.record_event(
            event_type="update",
            artifact_name=f"recent-artifact-{i}",
            artifact_type="agent",
            collection_name="default",
            metadata={"timestamp": now.isoformat()},
        )

    return {
        **workspace,
        "old_timestamp": old_time,
        "medium_timestamp": medium_time,
        "recent_timestamp": now,
    }


@pytest.fixture
def mock_artifact_manager(tmp_path):
    """Create a mock ArtifactManager for integration testing.

    Returns:
        Mock manager that simulates artifact operations
    """
    from unittest.mock import MagicMock

    manager = MagicMock()

    # Create fake collection directory
    collection_dir = tmp_path / "collection"
    collection_dir.mkdir()

    # Mock methods
    manager.get_collection_dir.return_value = collection_dir
    manager.list_artifacts.return_value = []
    manager.get_artifact_size.return_value = 1024 * 1024  # 1MB

    return manager


def create_test_events(
    db: AnalyticsDB,
    count: int,
    artifact_name: str = "test-artifact",
    artifact_type: str = "skill",
    days_spread: int = 7,
) -> List[Dict]:
    """Helper to create test events in bulk.

    Args:
        db: AnalyticsDB instance
        count: Number of events to create
        artifact_name: Name of artifact
        artifact_type: Type of artifact
        days_spread: Number of days to spread events across

    Returns:
        List of created event dictionaries
    """
    start_time = datetime.now() - timedelta(days=days_spread)
    events = []

    for i in range(count):
        days_offset = (i / count) * days_spread
        event_time = start_time + timedelta(days=days_offset)

        event_type = ["deploy", "update", "sync", "search"][i % 4]

        db.record_event(
            event_type=event_type,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name="default",
            metadata={"timestamp": event_time.isoformat()},
        )

        events.append(
            {
                "event_type": event_type,
                "artifact_name": artifact_name,
                "timestamp": event_time.isoformat(),
            }
        )

    return events


# Export helper
pytest.create_test_events = create_test_events
