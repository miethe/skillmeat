#!/usr/bin/env python3
"""
SkillMeat Test Failure Parser

Parses test results from various test frameworks (pytest, Jest, Playwright)
and generates actionable reports for automated triage.

Usage:
    python scripts/parse_test_failures.py [--input-dir DIR] [--output FILE]

Supported formats:
    - pytest JUnit XML
    - Jest JSON output
    - Playwright JSON reports
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET


class TestFailure:
    """Represents a single test failure"""

    def __init__(
        self,
        name: str,
        suite: str,
        message: str,
        framework: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ):
        self.name = name
        self.suite = suite
        self.message = message
        self.framework = framework
        self.file_path = file_path
        self.line_number = line_number

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "suite": self.suite,
            "message": self.message,
            "framework": self.framework,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }

    def to_markdown(self) -> str:
        """Convert to Markdown format for reports"""
        md = f"#### {self.name}\n\n"
        md += f"**Suite:** {self.suite}\n"
        md += f"**Framework:** {self.framework}\n"

        if self.file_path:
            md += f"**File:** `{self.file_path}`"
            if self.line_number:
                md += f":{self.line_number}"
            md += "\n"

        md += f"\n**Error:**\n```\n{self.message}\n```\n"
        return md


class TestFailureParser:
    """Parses test failures from multiple frameworks"""

    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.failures: List[TestFailure] = []

    def parse_all(self):
        """Parse all test result files in the input directory"""
        if not self.input_dir.exists():
            print(f"Warning: Input directory {self.input_dir} does not exist")
            return

        # Parse pytest results
        self._parse_pytest_junit()

        # Parse Jest results
        self._parse_jest_json()

        # Parse Playwright results
        self._parse_playwright_json()

    def _parse_pytest_junit(self):
        """Parse pytest JUnit XML output"""
        junit_files = list(self.input_dir.rglob("junit*.xml")) + list(
            self.input_dir.rglob("pytest*.xml")
        )

        for junit_file in junit_files:
            try:
                tree = ET.parse(junit_file)
                root = tree.getroot()

                # Handle both <testsuites> and <testsuite> root elements
                testsuites = root.findall(".//testsuite")
                if not testsuites:
                    testsuites = [root] if root.tag == "testsuite" else []

                for testsuite in testsuites:
                    suite_name = testsuite.get("name", "Unknown Suite")

                    for testcase in testsuite.findall("testcase"):
                        failure = testcase.find("failure")
                        error = testcase.find("error")

                        if failure is not None or error is not None:
                            element = failure if failure is not None else error
                            test_name = testcase.get("name", "Unknown Test")
                            message = element.get("message", "")
                            text = element.text or ""

                            # Extract file and line info from classname
                            file_path = testcase.get("file")
                            line_number = testcase.get("line")
                            if line_number:
                                try:
                                    line_number = int(line_number)
                                except ValueError:
                                    line_number = None

                            self.failures.append(
                                TestFailure(
                                    name=test_name,
                                    suite=suite_name,
                                    message=f"{message}\n{text}".strip(),
                                    framework="pytest",
                                    file_path=file_path,
                                    line_number=line_number,
                                )
                            )

            except ET.ParseError as e:
                print(f"Warning: Failed to parse {junit_file}: {e}")
            except Exception as e:
                print(f"Error processing {junit_file}: {e}")

    def _parse_jest_json(self):
        """Parse Jest JSON output"""
        jest_files = list(self.input_dir.rglob("jest-results*.json")) + list(
            self.input_dir.rglob("**/coverage/coverage-final.json")
        )

        for jest_file in jest_files:
            try:
                with open(jest_file, "r") as f:
                    data = json.load(f)

                # Handle different Jest output formats
                test_results = data.get("testResults", [])

                for test_result in test_results:
                    file_path = test_result.get("name", "Unknown File")
                    assertions = test_result.get("assertionResults", [])

                    for assertion in assertions:
                        if assertion.get("status") == "failed":
                            test_name = assertion.get("title", "Unknown Test")
                            ancestor_titles = assertion.get("ancestorTitles", [])
                            suite_name = " > ".join(ancestor_titles) if ancestor_titles else "Jest Suite"

                            failure_messages = assertion.get("failureMessages", [])
                            message = "\n".join(failure_messages) if failure_messages else "Test failed"

                            self.failures.append(
                                TestFailure(
                                    name=test_name,
                                    suite=suite_name,
                                    message=message,
                                    framework="jest",
                                    file_path=file_path,
                                )
                            )

            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON in {jest_file}: {e}")
            except Exception as e:
                print(f"Error processing {jest_file}: {e}")

    def _parse_playwright_json(self):
        """Parse Playwright JSON reports"""
        playwright_files = list(self.input_dir.rglob("results.json"))

        for pw_file in playwright_files:
            try:
                with open(pw_file, "r") as f:
                    data = json.load(f)

                suites = data.get("suites", [])

                for suite in suites:
                    self._parse_playwright_suite(suite)

            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON in {pw_file}: {e}")
            except Exception as e:
                print(f"Error processing {pw_file}: {e}")

    def _parse_playwright_suite(self, suite: Dict[str, Any], parent_title: str = ""):
        """Recursively parse Playwright test suite"""
        suite_title = suite.get("title", "")
        full_title = f"{parent_title} > {suite_title}" if parent_title else suite_title

        # Parse specs in this suite
        specs = suite.get("specs", [])
        for spec in specs:
            spec_title = spec.get("title", "Unknown Test")
            file_path = spec.get("file")

            tests = spec.get("tests", [])
            for test in tests:
                results = test.get("results", [])
                for result in results:
                    if result.get("status") in ["failed", "timedOut"]:
                        error = result.get("error", {})
                        message = error.get("message", "Test failed")

                        self.failures.append(
                            TestFailure(
                                name=spec_title,
                                suite=full_title or "Playwright Suite",
                                message=message,
                                framework="playwright",
                                file_path=file_path,
                            )
                        )

        # Parse nested suites
        for child_suite in suite.get("suites", []):
            self._parse_playwright_suite(child_suite, full_title)

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary of test failures"""
        summary = {
            "total_failures": len(self.failures),
            "by_framework": {},
            "by_suite": {},
            "failures": [f.to_dict() for f in self.failures],
        }

        # Count by framework
        for failure in self.failures:
            framework = failure.framework
            summary["by_framework"][framework] = summary["by_framework"].get(framework, 0) + 1

            suite = failure.suite
            summary["by_suite"][suite] = summary["by_suite"].get(suite, 0) + 1

        return summary

    def generate_markdown_summary(self) -> str:
        """Generate Markdown summary of failures"""
        if not self.failures:
            return "No test failures detected.\n"

        md = f"### Test Failures Summary\n\n"
        md += f"**Total Failures:** {len(self.failures)}\n\n"

        # By framework
        by_framework = {}
        for failure in self.failures:
            by_framework[failure.framework] = by_framework.get(failure.framework, 0) + 1

        md += "**By Framework:**\n"
        for framework, count in sorted(by_framework.items()):
            md += f"- {framework}: {count}\n"
        md += "\n"

        # Detailed failures
        md += "### Detailed Failures\n\n"

        current_framework = None
        for failure in sorted(self.failures, key=lambda f: (f.framework, f.suite, f.name)):
            if current_framework != failure.framework:
                current_framework = failure.framework
                md += f"### {current_framework.upper()} Failures\n\n"

            md += failure.to_markdown()
            md += "\n---\n\n"

        return md


def main():
    parser = argparse.ArgumentParser(
        description="Parse test failures from multiple frameworks"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("test-results"),
        help="Directory containing test result files (default: test-results)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test-failures.json"),
        help="Output JSON file (default: test-failures.json)",
    )

    args = parser.parse_args()

    print(f"Parsing test failures from: {args.input_dir}")

    failure_parser = TestFailureParser(args.input_dir)
    failure_parser.parse_all()

    summary = failure_parser.generate_summary()

    # Write JSON summary
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"JSON summary written to: {args.output}")

    # Write Markdown summary
    md_output = args.output.with_suffix(".md")
    markdown_summary = failure_parser.generate_markdown_summary()
    with open(md_output, "w") as f:
        f.write(markdown_summary)
    print(f"Markdown summary written to: {md_output}")

    # Write plain text summary for GitHub Actions
    text_summary_path = Path("test-failures-summary.txt")
    text_summary = f"Total failures: {summary['total_failures']}\n\n"
    for framework, count in summary["by_framework"].items():
        text_summary += f"{framework}: {count} failures\n"

    with open(text_summary_path, "w") as f:
        f.write(text_summary)

    print(f"\nFound {summary['total_failures']} test failures")

    # Exit with error code if failures found
    sys.exit(1 if summary["total_failures"] > 0 else 0)


if __name__ == "__main__":
    main()
