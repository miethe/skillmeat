#!/usr/bin/env python3
"""Demo script for ContextBooster - context-aware artifact scoring."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring import ContextBooster, ProjectContext

# Import tomli_w for writing TOML files
import tomli_w


def demo_react_project():
    """Demonstrate boosting in a React project."""
    print("\n" + "=" * 60)
    print("Demo: React Project with TypeScript")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create a React project with TypeScript
        package_json = {
            "name": "my-react-app",
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/react": "^18.0.0",
            },
        }
        (project_root / "package.json").write_text(json.dumps(package_json, indent=2))

        # Create booster
        booster = ContextBooster(project_root=project_root)

        # Show detected context
        context = booster.context
        print(f"\nDetected Context:")
        print(f"  Language: {context.language}")
        print(f"  Framework: {context.framework}")
        print(f"  Package Manager: {context.package_manager}")
        print(f"  Additional Tags: {context.additional_tags}")

        # Test various artifacts
        artifacts = [
            ArtifactMetadata(
                title="React Hooks Collection",
                description="Useful custom React hooks",
                tags=["react", "hooks"],
            ),
            ArtifactMetadata(
                title="TypeScript Utilities",
                description="TypeScript helper functions",
                tags=["typescript", "utilities"],
            ),
            ArtifactMetadata(
                title="Python Testing Framework",
                description="Python test utilities",
                tags=["python", "testing"],
            ),
        ]

        print("\n\nArtifact Scoring:")
        print("-" * 60)
        base_score = 75.0

        for artifact in artifacts:
            boost = booster.get_boost(artifact)
            boosted_score = booster.apply_boost(artifact, base_score)
            boost_pct = (boost - 1.0) * 100

            print(f"\n{artifact.title}")
            print(f"  Tags: {', '.join(artifact.tags or [])}")
            print(f"  Base Score: {base_score:.1f}")
            print(f"  Boost: {boost:.2f}x ({boost_pct:+.0f}%)")
            print(f"  Final Score: {boosted_score:.1f}")


def demo_python_fastapi_project():
    """Demonstrate boosting in a Python FastAPI project."""
    print("\n" + "=" * 60)
    print("Demo: Python FastAPI Project")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create a Python FastAPI project
        pyproject = {
            "project": {
                "name": "my-api",
                "version": "0.1.0",
                "dependencies": [
                    "fastapi>=0.100.0",
                    "uvicorn[standard]>=0.20.0",
                    "sqlalchemy>=2.0.0",
                ],
            }
        }
        (project_root / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        # Create booster with custom multiplier
        booster = ContextBooster(project_root=project_root, boost_multiplier=1.15)

        # Show detected context
        context = booster.context
        print(f"\nDetected Context:")
        print(f"  Language: {context.language}")
        print(f"  Framework: {context.framework}")
        print(f"  Package Manager: {context.package_manager}")
        print(f"  Additional Tags: {context.additional_tags}")

        # Test various artifacts
        artifacts = [
            ArtifactMetadata(
                title="FastAPI Authentication",
                description="JWT authentication for FastAPI",
                tags=["fastapi", "auth", "security"],
            ),
            ArtifactMetadata(
                title="Python Data Validator",
                description="Data validation utilities",
                tags=["python", "validation"],
            ),
            ArtifactMetadata(
                title="React Dashboard",
                description="Admin dashboard components",
                tags=["react", "ui"],
            ),
        ]

        print("\n\nArtifact Scoring:")
        print("-" * 60)
        base_score = 80.0

        for artifact in artifacts:
            boost = booster.get_boost(artifact)
            boosted_score = booster.apply_boost(artifact, base_score)
            boost_pct = (boost - 1.0) * 100

            print(f"\n{artifact.title}")
            print(f"  Tags: {', '.join(artifact.tags or [])}")
            print(f"  Base Score: {base_score:.1f}")
            print(f"  Boost: {boost:.2f}x ({boost_pct:+.0f}%)")
            print(f"  Final Score: {boosted_score:.1f}")


def demo_no_context():
    """Demonstrate behavior when no project context is found."""
    print("\n" + "=" * 60)
    print("Demo: No Project Context")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        # No manifest files created

        booster = ContextBooster(project_root=project_root)

        context = booster.context
        print(f"\nDetected Context:")
        print(f"  Language: {context.language}")
        print(f"  Framework: {context.framework}")
        print(f"  Package Manager: {context.package_manager}")
        print(f"  Additional Tags: {context.additional_tags}")

        artifact = ArtifactMetadata(
            title="Generic Tool",
            description="A useful utility",
            tags=["utilities"],
        )

        base_score = 75.0
        boost = booster.get_boost(artifact)
        boosted_score = booster.apply_boost(artifact, base_score)

        print("\n\nArtifact Scoring:")
        print("-" * 60)
        print(f"\n{artifact.title}")
        print(f"  Tags: {', '.join(artifact.tags or [])}")
        print(f"  Base Score: {base_score:.1f}")
        print(f"  Boost: {boost:.2f}x (no context detected)")
        print(f"  Final Score: {boosted_score:.1f}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ContextBooster Demo")
    print("Context-aware artifact scoring based on project type")
    print("=" * 60)

    demo_react_project()
    demo_python_fastapi_project()
    demo_no_context()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60 + "\n")
