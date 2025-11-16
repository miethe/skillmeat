"""Usage Reports API for SkillMeat analytics.

Provides APIs to query analytics data and generate insights about artifact usage
patterns, enabling cleanup suggestions, usage analysis, and trend reporting.
"""

import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import ConfigManager
from ..storage.analytics import AnalyticsDB
from ..utils.logging import redact_path

logger = logging.getLogger(__name__)


class UsageReportManager:
    """Manages usage reports and analytics queries.

    Provides high-level APIs for querying analytics data, generating usage
    reports, cleanup suggestions, and trend analysis.

    Features:
    - Artifact usage statistics
    - Top artifacts by various metrics
    - Unused artifact detection
    - Cleanup suggestions with size estimation
    - Usage trend analysis
    - Report export to JSON/CSV

    Example:
        >>> config = ConfigManager()
        >>> manager = UsageReportManager(config)
        >>> usage = manager.get_artifact_usage("canvas")
        >>> print(f"Total events: {usage['total_events']}")
        >>> cleanup = manager.get_cleanup_suggestions()
        >>> print(f"Unused artifacts: {len(cleanup['unused_90_days'])}")
    """

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        db_path: Optional[Path] = None,
    ):
        """Initialize usage report manager.

        Args:
            config: Configuration manager instance. If None, creates new instance.
            db_path: Override analytics database path. If None, uses config setting.

        Raises:
            RuntimeError: If analytics is disabled in config
        """
        self.config = config or ConfigManager()

        # Check if analytics is enabled
        if not self.config.is_analytics_enabled():
            logger.warning("Analytics is disabled. Reports will be empty.")
            self._analytics_enabled = False
            self.db = None
        else:
            self._analytics_enabled = True
            # Use provided path or get from config
            if db_path is None:
                db_path = self.config.get_analytics_db_path()
            self.db = AnalyticsDB(db_path)

        # Cache collection directory for size calculations
        self._collection_dir = self.config.get_collections_dir()

    def get_artifact_usage(
        self,
        artifact_name: Optional[str] = None,
        artifact_type: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics for artifact(s).

        Args:
            artifact_name: Filter by artifact name (optional)
            artifact_type: Filter by artifact type (skill, command, agent) (optional)
            collection_name: Filter by collection name (optional)

        Returns:
            Dictionary containing usage statistics:
            - artifact_name: Name of artifact
            - artifact_type: Type of artifact
            - first_used: Timestamp of first use
            - last_used: Timestamp of last use
            - deploy_count: Number of deploy events
            - update_count: Number of update events
            - sync_count: Number of sync events
            - remove_count: Number of remove events
            - search_count: Number of search events
            - total_events: Total number of events
            - days_since_last_use: Days since last use
            - usage_trend: "increasing", "decreasing", or "stable"

            If querying multiple artifacts, returns list under "artifacts" key.

        Example:
            >>> usage = manager.get_artifact_usage("canvas", artifact_type="skill")
            >>> print(f"Last used: {usage['last_used']}")
            >>> print(f"Total deploys: {usage['deploy_count']}")
        """
        if not self._analytics_enabled or self.db is None:
            return self._empty_usage_response(artifact_name)

        # Query usage summary
        summary = self.db.get_usage_summary(
            artifact_name=artifact_name, artifact_type=artifact_type
        )

        if not summary:
            return self._empty_usage_response(artifact_name)

        # If single artifact, return single dict
        if artifact_name and len(summary) == 1:
            result = summary[0]
            # Add computed fields
            result["days_since_last_use"] = self._calculate_days_since(
                result["last_used"]
            )
            result["usage_trend"] = self._calculate_usage_trend(result["artifact_name"])
            return result

        # Multiple artifacts - add computed fields to each
        for artifact in summary:
            artifact["days_since_last_use"] = self._calculate_days_since(
                artifact["last_used"]
            )
            artifact["usage_trend"] = self._calculate_usage_trend(
                artifact["artifact_name"]
            )

        return {"artifacts": summary, "total_count": len(summary)}

    def get_top_artifacts(
        self,
        artifact_type: Optional[str] = None,
        metric: str = "total_events",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top artifacts by usage metric.

        Args:
            artifact_type: Filter by artifact type (skill, command, agent) (optional)
            metric: Sort by metric (total_events, deploy_count, update_count,
                sync_count, search_count) (default: total_events)
            limit: Maximum number of results (default: 10)

        Returns:
            List of artifact usage dictionaries sorted by metric (descending)

        Raises:
            ValueError: If metric is invalid

        Example:
            >>> top = manager.get_top_artifacts(artifact_type="skill", limit=5)
            >>> for artifact in top:
            ...     print(f"{artifact['artifact_name']}: {artifact['total_events']}")
        """
        if not self._analytics_enabled or self.db is None:
            return []

        valid_metrics = {
            "total_events",
            "deploy_count",
            "update_count",
            "sync_count",
            "remove_count",
            "search_count",
        }

        if metric not in valid_metrics:
            raise ValueError(
                f"Invalid metric '{metric}'. "
                f"Must be one of: {', '.join(sorted(valid_metrics))}"
            )

        # Build custom query for non-default metrics
        if metric == "total_events":
            # Use optimized built-in method
            return self.db.get_top_artifacts(artifact_type=artifact_type, limit=limit)

        # Custom query for other metrics
        query = f"SELECT * FROM usage_summary WHERE 1=1"
        params = []

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)

        query += f" ORDER BY {metric} DESC, total_events DESC LIMIT ?"
        params.append(limit)

        cursor = self.db.connection.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_unused_artifacts(
        self,
        days_threshold: int = 90,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find artifacts not used in X days.

        Args:
            days_threshold: Number of days without activity (default: 90)
            collection_name: Filter by collection name (optional)

        Returns:
            List of unused artifacts with metadata:
            - artifact_name: Name of artifact
            - artifact_type: Type of artifact
            - last_used: Timestamp of last use
            - days_ago: Days since last use
            - total_events: Total number of events (historical)

        Example:
            >>> unused = manager.get_unused_artifacts(days_threshold=60)
            >>> for artifact in unused:
            ...     print(f"{artifact['artifact_name']}: {artifact['days_ago']} days")
        """
        if not self._analytics_enabled or self.db is None:
            return []

        if days_threshold < 0:
            raise ValueError("days_threshold must be non-negative")

        cutoff = datetime.now() - timedelta(days=days_threshold)

        # Query usage_summary for artifacts with last_used before cutoff
        query = """
            SELECT artifact_name, artifact_type, last_used, total_events
            FROM usage_summary
            WHERE last_used < ?
        """
        params = [cutoff]

        # Note: collection filtering requires querying events table
        # which is more expensive. Skip for now unless needed.
        if collection_name:
            logger.warning(
                "collection_name filtering for unused artifacts requires "
                "events table scan. Consider using without filter."
            )

        query += " ORDER BY last_used ASC"

        cursor = self.db.connection.execute(query, params)
        results = []

        for row in cursor.fetchall():
            artifact = dict(row)
            artifact["days_ago"] = self._calculate_days_since(artifact["last_used"])
            results.append(artifact)

        return results

    def get_cleanup_suggestions(
        self,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate cleanup suggestions based on usage patterns.

        Analyzes artifact usage and suggests candidates for removal based on:
        - Artifacts unused for 90+ days
        - Artifacts never deployed
        - Artifacts with low usage (<5 events) and old (60+ days)

        Args:
            collection_name: Filter by collection name (optional)

        Returns:
            Dictionary containing:
            - unused_90_days: List of artifacts unused for 90+ days
            - never_deployed: List of artifacts with 0 deployments
            - low_usage: List of artifacts with <5 events and 60+ days old
            - total_reclaimable_mb: Estimated disk space reclaimable (MB)
            - summary: Text summary of suggestions

        Example:
            >>> suggestions = manager.get_cleanup_suggestions()
            >>> print(suggestions['summary'])
            >>> for artifact in suggestions['unused_90_days']:
            ...     print(f"Remove {artifact['name']}: {artifact['days_ago']} days old")
        """
        if not self._analytics_enabled or self.db is None:
            return {
                "unused_90_days": [],
                "never_deployed": [],
                "low_usage": [],
                "total_reclaimable_mb": 0.0,
                "summary": "Analytics disabled - no suggestions available",
            }

        suggestions = {
            "unused_90_days": [],
            "never_deployed": [],
            "low_usage": [],
        }

        # 1. Artifacts unused for 90+ days
        unused = self.get_unused_artifacts(days_threshold=90)
        for artifact in unused:
            suggestions["unused_90_days"].append(
                {
                    "name": artifact["artifact_name"],
                    "type": artifact["artifact_type"],
                    "last_used": artifact["last_used"],
                    "days_ago": artifact["days_ago"],
                }
            )

        # 2. Never deployed artifacts
        query = """
            SELECT artifact_name, artifact_type, first_used, total_events
            FROM usage_summary
            WHERE deploy_count = 0
            ORDER BY total_events ASC
        """
        cursor = self.db.connection.execute(query)

        for row in cursor.fetchall():
            artifact = dict(row)
            days_since_added = self._calculate_days_since(artifact["first_used"])

            suggestions["never_deployed"].append(
                {
                    "name": artifact["artifact_name"],
                    "type": artifact["artifact_type"],
                    "added": artifact["first_used"],
                    "days_since_added": days_since_added,
                    "total_events": artifact["total_events"],
                }
            )

        # 3. Low usage artifacts (< 5 events, 60+ days old)
        cutoff = datetime.now() - timedelta(days=60)
        query = """
            SELECT artifact_name, artifact_type, first_used, total_events
            FROM usage_summary
            WHERE total_events < 5 AND first_used < ?
            ORDER BY total_events ASC
        """
        cursor = self.db.connection.execute(query, (cutoff,))

        for row in cursor.fetchall():
            artifact = dict(row)
            days_since_added = self._calculate_days_since(artifact["first_used"])

            suggestions["low_usage"].append(
                {
                    "name": artifact["artifact_name"],
                    "type": artifact["artifact_type"],
                    "total_events": artifact["total_events"],
                    "days_since_added": days_since_added,
                }
            )

        # 4. Calculate reclaimable size
        all_suggestions = set()
        for category in ["unused_90_days", "never_deployed", "low_usage"]:
            all_suggestions.update(s["name"] for s in suggestions[category])

        total_size_bytes = 0
        for artifact_name in all_suggestions:
            size = self._estimate_artifact_size(artifact_name)
            total_size_bytes += size

        suggestions["total_reclaimable_mb"] = round(total_size_bytes / (1024 * 1024), 2)

        # 5. Generate summary
        summary_parts = []
        if suggestions["unused_90_days"]:
            summary_parts.append(
                f"{len(suggestions['unused_90_days'])} artifacts unused for 90+ days"
            )
        if suggestions["never_deployed"]:
            summary_parts.append(
                f"{len(suggestions['never_deployed'])} artifacts never deployed"
            )
        if suggestions["low_usage"]:
            summary_parts.append(
                f"{len(suggestions['low_usage'])} artifacts with low usage"
            )

        if summary_parts:
            suggestions["summary"] = (
                f"Found {sum(len(suggestions[k]) for k in ['unused_90_days', 'never_deployed', 'low_usage'])} "
                f"cleanup candidates: {'; '.join(summary_parts)}. "
                f"Reclaimable space: {suggestions['total_reclaimable_mb']} MB"
            )
        else:
            suggestions["summary"] = "No cleanup suggestions - all artifacts in use"

        return suggestions

    def get_usage_trends(
        self,
        artifact_name: Optional[str] = None,
        time_period: str = "30d",
    ) -> Dict[str, Any]:
        """Get usage trends over time period.

        Args:
            artifact_name: Optional artifact to analyze (if None, analyzes all)
            time_period: Time period for analysis - "7d", "30d", "90d", or "all"
                (default: "30d")

        Returns:
            Dictionary containing:
            - period: Time period analyzed
            - deploy_trend: List of {date, count} for deploys
            - update_trend: List of {date, count} for updates
            - sync_trend: List of {date, count} for syncs
            - search_trend: List of {date, count} for searches
            - total_events_by_day: Dict mapping date to total count

        Raises:
            ValueError: If time_period is invalid

        Example:
            >>> trends = manager.get_usage_trends("canvas", time_period="7d")
            >>> for day in trends['deploy_trend']:
            ...     print(f"{day['date']}: {day['count']} deploys")
        """
        if not self._analytics_enabled or self.db is None:
            return {
                "period": time_period,
                "deploy_trend": [],
                "update_trend": [],
                "sync_trend": [],
                "search_trend": [],
                "total_events_by_day": {},
            }

        # Parse time period
        valid_periods = {"7d", "30d", "90d", "all"}
        if time_period not in valid_periods:
            raise ValueError(
                f"Invalid time_period '{time_period}'. "
                f"Must be one of: {', '.join(sorted(valid_periods))}"
            )

        # Calculate cutoff date
        if time_period == "all":
            cutoff = None
        else:
            days = int(time_period[:-1])  # Extract number from "30d"
            cutoff = datetime.now() - timedelta(days=days)

        # Build base query
        query = """
            SELECT
                DATE(timestamp) as date,
                event_type,
                COUNT(*) as count
            FROM events
            WHERE 1=1
        """
        params = []

        if artifact_name:
            query += " AND artifact_name = ?"
            params.append(artifact_name)

        if cutoff:
            query += " AND timestamp >= ?"
            params.append(cutoff)

        query += " GROUP BY DATE(timestamp), event_type ORDER BY date ASC"

        # Execute query
        cursor = self.db.connection.execute(query, params)
        rows = cursor.fetchall()

        # Organize results by event type
        trends = {
            "period": time_period,
            "deploy_trend": [],
            "update_trend": [],
            "sync_trend": [],
            "search_trend": [],
            "remove_trend": [],
            "total_events_by_day": {},
        }

        for row in rows:
            date_str = row[0]
            event_type = row[1]
            count = row[2]

            # Add to event type trend
            trend_key = f"{event_type}_trend"
            if trend_key in trends:
                trends[trend_key].append({"date": date_str, "count": count})

            # Add to total
            if date_str not in trends["total_events_by_day"]:
                trends["total_events_by_day"][date_str] = 0
            trends["total_events_by_day"][date_str] += count

        return trends

    def export_usage_report(
        self,
        output_path: Path,
        format: str = "json",
        collection_name: Optional[str] = None,
    ) -> None:
        """Export comprehensive usage report to file.

        Args:
            output_path: Path where report will be saved
            format: Export format - "json" or "csv" (default: "json")
            collection_name: Filter by collection name (optional)

        Raises:
            ValueError: If format is invalid
            IOError: If file cannot be written

        Example:
            >>> manager.export_usage_report(
            ...     Path("usage_report.json"),
            ...     format="json"
            ... )
        """
        if format not in {"json", "csv"}:
            raise ValueError(f"Invalid format '{format}'. Must be 'json' or 'csv'")

        # Generate comprehensive report
        report = {
            "generated_at": datetime.now().isoformat(),
            "report_type": "usage_report",
            "filters": {
                "collection_name": collection_name,
            },
            "summary": {},
            "top_artifacts": [],
            "cleanup_suggestions": {},
            "trends_30d": {},
        }

        if self._analytics_enabled and self.db:
            # Add database stats
            report["summary"] = self.db.get_stats()

            # Add top artifacts
            report["top_artifacts"] = self.get_top_artifacts(limit=20)

            # Add cleanup suggestions
            report["cleanup_suggestions"] = self.get_cleanup_suggestions(
                collection_name=collection_name
            )

            # Add 30-day trends
            report["trends_30d"] = self.get_usage_trends(time_period="30d")

        # Export based on format
        if format == "json":
            self._export_json(report, output_path)
        else:  # csv
            self._export_csv(report, output_path)

    def _export_json(self, report: Dict[str, Any], output_path: Path) -> None:
        """Export report as JSON with pretty printing.

        Args:
            report: Report dictionary to export
            output_path: Path to output file
        """

        class DateTimeEncoder(json.JSONEncoder):
            """JSON encoder that handles datetime objects."""

            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, cls=DateTimeEncoder)

        logger.info(f"Exported JSON report to {redact_path(output_path)}")

    def _export_csv(self, report: Dict[str, Any], output_path: Path) -> None:
        """Export report as CSV (flattened top artifacts).

        Args:
            report: Report dictionary to export
            output_path: Path to output file

        Note:
            CSV export only includes top artifacts table due to format limitations.
            For full report, use JSON format.
        """
        top_artifacts = report.get("top_artifacts", [])

        if not top_artifacts:
            logger.warning("No artifacts to export to CSV")
            return

        # Write CSV
        with open(output_path, "w", newline="") as f:
            fieldnames = top_artifacts[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(top_artifacts)

        logger.info(f"Exported CSV report to {redact_path(output_path)}")

    # Helper methods

    def _empty_usage_response(self, artifact_name: Optional[str]) -> Dict[str, Any]:
        """Return empty usage response structure.

        Args:
            artifact_name: Name of artifact (if single artifact query)

        Returns:
            Empty usage dictionary
        """
        if artifact_name:
            return {
                "artifact_name": artifact_name,
                "artifact_type": None,
                "first_used": None,
                "last_used": None,
                "deploy_count": 0,
                "update_count": 0,
                "sync_count": 0,
                "remove_count": 0,
                "search_count": 0,
                "total_events": 0,
                "days_since_last_use": None,
                "usage_trend": "stable",
            }
        return {"artifacts": [], "total_count": 0}

    def _calculate_days_since(self, timestamp: Optional[str]) -> Optional[int]:
        """Calculate days since timestamp.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            Number of days since timestamp, or None if timestamp is None
        """
        if timestamp is None:
            return None

        # Parse timestamp (handle both ISO and SQLite formats)
        if isinstance(timestamp, str):
            # Try ISO format first
            try:
                dt = datetime.fromisoformat(timestamp)
            except ValueError:
                # Try SQLite datetime format
                try:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {timestamp}")
                    return None
        else:
            # Already a datetime object
            dt = timestamp

        delta = datetime.now() - dt
        return delta.days

    def _calculate_usage_trend(
        self, artifact_name: str, days: int = 30
    ) -> str:
        """Calculate usage trend for artifact.

        Args:
            artifact_name: Name of artifact
            days: Number of days to analyze (default: 30)

        Returns:
            "increasing", "decreasing", or "stable"
        """
        if not self._analytics_enabled or self.db is None:
            return "stable"

        # Get events for last N days, grouped by week
        cutoff = datetime.now() - timedelta(days=days)

        query = """
            SELECT
                (julianday(timestamp) - julianday(?)) / 7 as week_num,
                COUNT(*) as count
            FROM events
            WHERE artifact_name = ? AND timestamp >= ?
            GROUP BY week_num
            ORDER BY week_num ASC
        """

        cursor = self.db.connection.execute(query, (cutoff, artifact_name, cutoff))
        rows = cursor.fetchall()

        if len(rows) < 2:
            return "stable"

        # Simple linear trend: compare first half vs second half
        counts = [row[1] for row in rows]
        mid = len(counts) // 2
        first_half_avg = sum(counts[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(counts[mid:]) / (len(counts) - mid) if len(counts) - mid > 0 else 0

        # Calculate percentage change
        if first_half_avg == 0:
            return "increasing" if second_half_avg > 0 else "stable"

        change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        # Threshold: ±20% is significant
        if change_pct > 20:
            return "increasing"
        elif change_pct < -20:
            return "decreasing"
        else:
            return "stable"

    def _estimate_artifact_size(self, artifact_name: str) -> int:
        """Estimate disk size of artifact in bytes.

        Args:
            artifact_name: Name of artifact

        Returns:
            Size in bytes (0 if not found or error)
        """
        if not self._collection_dir:
            return 0

        # Get active collection name
        try:
            collection_name = self.config.get_active_collection()
            collection_path = self.config.get_collection_path(collection_name)
        except Exception as e:
            logger.warning(f"Could not get active collection: {e}")
            return 0

        # Search for artifact in collection
        # Artifacts are typically in: ~/.skillmeat/collections/<collection>/skills/<artifact_name>
        artifact_path = collection_path / "skills" / artifact_name

        if not artifact_path.exists():
            # Try other artifact types
            for artifact_type in ["commands", "agents"]:
                artifact_path = collection_path / artifact_type / artifact_name
                if artifact_path.exists():
                    break
            else:
                # Not found
                return 0

        # Calculate directory size recursively
        total_size = 0
        try:
            for item in artifact_path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(f"Could not calculate size for {artifact_name}: {e}")
            return 0

        return total_size

    def close(self) -> None:
        """Close database connection.

        Should be called when done with reports to release resources.
        """
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures database is closed."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensures database is closed."""
        self.close()
