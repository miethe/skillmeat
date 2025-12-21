#!/usr/bin/env python3
"""
Analyze beta program feedback and generate comprehensive report.

This script processes feedback collected during the SkillMeat beta program
and generates actionable insights for the development team.

Usage:
    python scripts/analyze_beta_feedback.py
    python scripts/analyze_beta_feedback.py --feedback-dir /path/to/feedback/files
    python scripts/analyze_beta_feedback.py --output report.md
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import statistics


class BetaFeedbackAnalyzer:
    """Analyze beta feedback and generate insights."""

    def __init__(self, feedback_dir: str = "docs/user/beta/feedback", output_file: Optional[str] = None):
        """Initialize analyzer with feedback directory."""
        self.feedback_dir = Path(feedback_dir)
        self.output_file = Path(output_file) if output_file else Path("docs/user/beta/feedback-report.md")
        self.feedback_data: List[Dict[str, Any]] = []
        self.bugs: List[Dict[str, Any]] = []
        self.feature_requests: List[Dict[str, Any]] = []
        self.satisfaction_ratings: Dict[str, List[float]] = defaultdict(list)

    def load_feedback(self) -> bool:
        """Load all feedback JSON files from directory."""
        if not self.feedback_dir.exists():
            print(f"Feedback directory not found: {self.feedback_dir}")
            return False

        json_files = list(self.feedback_dir.glob("*.json"))
        if not json_files:
            print(f"No feedback files found in {self.feedback_dir}")
            return False

        for file in json_files:
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.feedback_data.append(data)
                    self._extract_structured_data(data)
            except json.JSONDecodeError as e:
                print(f"Error parsing {file}: {e}")
                continue

        print(f"Loaded {len(self.feedback_data)} feedback responses")
        return len(self.feedback_data) > 0

    def _extract_structured_data(self, feedback: Dict[str, Any]) -> None:
        """Extract structured data from feedback for analysis."""
        # Extract bug reports
        for bug in feedback.get("bugs", []):
            self.bugs.append(bug)

        # Extract feature requests
        for feature in feedback.get("feature_requests", []):
            self.feature_requests.append(feature)

        # Extract satisfaction ratings
        for key, value in feedback.get("satisfaction_ratings", {}).items():
            if isinstance(value, (int, float)):
                self.satisfaction_ratings[key].append(float(value))

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate summary metrics from feedback data."""
        total_participants = len(self.feedback_data)
        if total_participants == 0:
            return {}

        # Calculate average ratings
        avg_ratings = {}
        for key, values in self.satisfaction_ratings.items():
            if values:
                avg = statistics.mean(values)
                stdev = statistics.stdev(values) if len(values) > 1 else 0
                avg_ratings[key] = {
                    "average": round(avg, 2),
                    "stdev": round(stdev, 2),
                    "min": min(values),
                    "max": max(values),
                    "responses": len(values),
                }

        # Calculate NPS
        nps_scores = [
            f.get("nps_score", 0) for f in self.feedback_data if "nps_score" in f
        ]
        nps = None
        if nps_scores:
            # NPS = (Promoters - Detractors) / Total
            promoters = sum(1 for s in nps_scores if s >= 9)
            detractors = sum(1 for s in nps_scores if s <= 6)
            nps = round(((promoters - detractors) / len(nps_scores)) * 100, 1)

        # Platform and role distribution
        platforms = Counter(f.get("platform", "Unknown") for f in self.feedback_data)
        roles = Counter(f.get("role", "Unknown") for f in self.feedback_data)

        # Usage metrics
        duration_distribution = Counter(
            f.get("usage_duration", "Unknown") for f in self.feedback_data
        )
        collection_sizes = Counter(
            f.get("collection_size", "Unknown") for f in self.feedback_data
        )

        # Completion rate (days active)
        completion_rate = self._calculate_completion_rate()

        return {
            "total_participants": total_participants,
            "completion_rate": completion_rate,
            "average_ratings": avg_ratings,
            "nps": nps,
            "platform_distribution": dict(platforms),
            "role_distribution": dict(roles),
            "duration_distribution": dict(duration_distribution),
            "collection_sizes": dict(collection_sizes),
        }

    def _calculate_completion_rate(self) -> float:
        """Calculate beta program completion rate."""
        if not self.feedback_data:
            return 0.0

        complete = sum(
            1 for f in self.feedback_data
            if f.get("survey_complete", False)
        )
        return round((complete / len(self.feedback_data)) * 100, 1)

    def categorize_bugs(self) -> Dict[str, Any]:
        """Categorize and prioritize bugs."""
        severity_counts = Counter()
        category_counts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        platform_bugs: Dict[str, int] = defaultdict(int)

        for bug in self.bugs:
            severity = bug.get("severity", "Unknown")
            category = bug.get("category", "Other")
            platform = bug.get("platform", "Unknown")

            severity_counts[severity] += 1
            category_counts[category].append(bug)
            platform_bugs[platform] += 1

        # Calculate blocker vs non-blocker
        blockers = sum(1 for b in self.bugs if b.get("severity") in ["P0", "P1"])

        return {
            "total_bugs": len(self.bugs),
            "blockers": blockers,
            "by_severity": dict(sorted(severity_counts.items())),
            "by_category": {k: len(v) for k, v in category_counts.items()},
            "by_platform": dict(platform_bugs),
            "details": dict(category_counts),
        }

    def categorize_features(self) -> Dict[str, Any]:
        """Categorize and prioritize feature requests."""
        priority_counts = Counter()
        category_counts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for feature in self.feature_requests:
            priority = feature.get("priority", "Medium")
            category = feature.get("category", "Enhancement")

            priority_counts[priority] += 1
            category_counts[category].append(feature)

        # Calculate top requests (by frequency)
        feature_names = Counter(f.get("name") for f in self.feature_requests)

        return {
            "total_requests": len(self.feature_requests),
            "by_priority": dict(priority_counts),
            "by_category": {k: len(v) for k, v in category_counts.items()},
            "top_requests": feature_names.most_common(10),
        }

    def generate_report(self) -> str:
        """Generate comprehensive feedback analysis report."""
        if not self.feedback_data:
            return "No feedback data to analyze."

        metrics = self.calculate_metrics()
        bugs = self.categorize_bugs()
        features = self.categorize_features()

        # Build report
        report_parts = []

        # Header
        report_parts.append("# SkillMeat Beta Program Feedback Report")
        report_parts.append("")
        report_parts.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report_parts.append("")

        # Executive Summary
        report_parts.append("## Executive Summary")
        report_parts.append("")
        report_parts.append(f"**Participants**: {metrics['total_participants']}")
        report_parts.append(f"**Completion Rate**: {metrics['completion_rate']:.1f}%")
        if metrics.get("nps") is not None:
            report_parts.append(f"**NPS Score**: {metrics['nps']}")
        report_parts.append(f"**Total Bugs Reported**: {bugs['total_bugs']}")
        report_parts.append(f"**Critical Issues**: {bugs['blockers']}")
        report_parts.append(f"**Feature Requests**: {features['total_requests']}")
        report_parts.append("")

        # Satisfaction Ratings
        report_parts.append("## Satisfaction Ratings")
        report_parts.append("")
        report_parts.append("| Aspect | Average | Std Dev | Min | Max | N |")
        report_parts.append("|--------|---------|---------|-----|-----|---|")
        for aspect, stats in sorted(metrics.get("average_ratings", {}).items()):
            report_parts.append(
                f"| {aspect} | {stats['average']}/5 | {stats['stdev']} | "
                f"{stats['min']} | {stats['max']} | {stats['responses']} |"
            )
        report_parts.append("")

        # Participant Distribution
        report_parts.append("## Participant Distribution")
        report_parts.append("")
        report_parts.append("### By Platform")
        for platform, count in sorted(
            metrics.get("platform_distribution", {}).items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / metrics["total_participants"]) * 100
            report_parts.append(f"- {platform}: {count} ({percentage:.1f}%)")
        report_parts.append("")

        report_parts.append("### By Role")
        for role, count in sorted(
            metrics.get("role_distribution", {}).items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / metrics["total_participants"]) * 100
            report_parts.append(f"- {role}: {count} ({percentage:.1f}%)")
        report_parts.append("")

        # Bug Analysis
        report_parts.append("## Bug Analysis")
        report_parts.append("")
        report_parts.append("### By Severity")
        for severity, count in sorted(bugs.get("by_severity", {}).items()):
            report_parts.append(f"- {severity}: {count}")
        report_parts.append("")

        report_parts.append("### By Category")
        for category, count in sorted(
            bugs.get("by_category", {}).items(), key=lambda x: x[1], reverse=True
        ):
            report_parts.append(f"- {category}: {count}")
        report_parts.append("")

        # Critical bugs detail
        if bugs["blockers"] > 0:
            report_parts.append("### Critical Issues (P0/P1)")
            report_parts.append("")
            critical_bugs = [
                b for b in self.bugs
                if b.get("severity") in ["P0", "P1"]
            ]
            for i, bug in enumerate(critical_bugs[:10], 1):
                report_parts.append(f"{i}. **{bug.get('title', 'Unknown')}**")
                report_parts.append(f"   - Severity: {bug.get('severity')}")
                report_parts.append(f"   - Category: {bug.get('category')}")
                report_parts.append(f"   - Description: {bug.get('description', 'N/A')}")
                report_parts.append("")

        # Feature Requests
        report_parts.append("## Feature Request Analysis")
        report_parts.append("")
        report_parts.append("### By Priority")
        for priority, count in sorted(
            features.get("by_priority", {}).items(),
            key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x[0], 3)
        ):
            report_parts.append(f"- {priority}: {count}")
        report_parts.append("")

        report_parts.append("### Top Requested Features")
        report_parts.append("")
        for feature_name, count in features.get("top_requests", [])[:5]:
            report_parts.append(f"- {feature_name}: {count} requests")
        report_parts.append("")

        # Recommendations
        report_parts.append("## Recommendations for GA Release")
        report_parts.append("")
        report_parts.extend(self._generate_recommendations(metrics, bugs, features))
        report_parts.append("")

        # Appendix
        report_parts.append("## Appendix: Raw Data")
        report_parts.append("")
        report_parts.append("### Metrics JSON")
        report_parts.append("```json")
        report_parts.append(json.dumps(metrics, indent=2))
        report_parts.append("```")
        report_parts.append("")
        report_parts.append("### Bugs JSON")
        report_parts.append("```json")
        report_parts.append(json.dumps(bugs, indent=2))
        report_parts.append("```")
        report_parts.append("")
        report_parts.append("### Features JSON")
        report_parts.append("```json")
        report_parts.append(json.dumps(features, indent=2))
        report_parts.append("```")

        return "\n".join(report_parts)

    def _generate_recommendations(
        self, metrics: Dict[str, Any], bugs: Dict[str, Any], features: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Check completion rate
        if metrics["completion_rate"] < 80:
            recommendations.append(
                f"**Engagement**: {metrics['completion_rate']:.1f}% completion rate is below target (80%). "
                "Consider follow-up outreach to inactive participants."
            )

        # Check blocker bugs
        if bugs["blockers"] > 0:
            recommendations.append(
                f"**Critical Issues**: {bugs['blockers']} P0/P1 bugs reported. "
                "All must be fixed before GA release. Current status: BLOCKER."
            )

        # Check satisfaction ratings
        avg_satisfaction = statistics.mean(
            stats["average"]
            for stats in metrics.get("average_ratings", {}).values()
        ) if metrics.get("average_ratings") else 0

        if avg_satisfaction < 4.0:
            recommendations.append(
                f"**User Satisfaction**: {avg_satisfaction:.1f}/5 is below target (4.0). "
                "Prioritize addressing top bug categories and UX issues."
            )

        # Check NPS
        if metrics.get("nps") and metrics["nps"] < 30:
            recommendations.append(
                f"**NPS Score**: {metrics['nps']} is below target. "
                "Focus on addressing detractor feedback before GA."
            )

        # Platform-specific issues
        if bugs.get("by_platform"):
            for platform, count in bugs["by_platform"].items():
                if count > bugs["total_bugs"] * 0.3:
                    recommendations.append(
                        f"**Platform**: {count} bugs on {platform} ({(count/bugs['total_bugs']*100):.1f}% of total). "
                        "May indicate platform-specific issues."
                    )

        # Feature requests
        if features["total_requests"] > 0:
            high_priority = features["by_priority"].get("High", 0)
            if high_priority > 0:
                recommendations.append(
                    f"**Features**: {high_priority} high-priority feature requests. "
                    "Assess which are critical for GA vs post-GA delivery."
                )

        # Default recommendations if no issues
        if not recommendations:
            recommendations = [
                "Beta program results are strong. All success criteria met.",
                "No critical blockers identified. GA release ready.",
                "Continue addressing medium-priority issues post-GA.",
            ]

        return [f"- {rec}" for rec in recommendations]

    def save_report(self, content: str) -> None:
        """Save report to file."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report saved: {self.output_file}")

    def run(self) -> bool:
        """Run complete analysis pipeline."""
        if not self.load_feedback():
            return False

        report = self.generate_report()
        self.save_report(report)
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)
        return True


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze SkillMeat beta program feedback"
    )
    parser.add_argument(
        "--feedback-dir",
        default="docs/user/beta/feedback",
        help="Directory containing feedback JSON files (default: docs/user/beta/feedback)",
    )
    parser.add_argument(
        "--output",
        default="docs/user/beta/feedback-report.md",
        help="Output report file (default: docs/user/beta/feedback-report.md)",
    )

    args = parser.parse_args()

    analyzer = BetaFeedbackAnalyzer(
        feedback_dir=args.feedback_dir, output_file=args.output
    )
    success = analyzer.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
