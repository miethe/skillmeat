"""Tests for context-aware scoring (ContextBooster)."""

import json
import sys
from pathlib import Path

import pytest

from skillmeat.core.artifact import ArtifactMetadata
from skillmeat.core.scoring.context_booster import ContextBooster, ProjectContext

# Handle tomli_w import for writing test TOML files
import tomli_w


class TestProjectContext:
    """Test ProjectContext dataclass."""

    def test_default_initialization(self):
        """Test ProjectContext with default values."""
        context = ProjectContext()
        assert context.language is None
        assert context.framework is None
        assert context.package_manager is None
        assert context.additional_tags == set()

    def test_explicit_initialization(self):
        """Test ProjectContext with explicit values."""
        context = ProjectContext(
            language="python",
            framework="fastapi",
            package_manager="uv",
            additional_tags={"async", "web"},
        )
        assert context.language == "python"
        assert context.framework == "fastapi"
        assert context.package_manager == "uv"
        assert context.additional_tags == {"async", "web"}


class TestContextBoosterDetection:
    """Test project type detection from manifests."""

    def test_detect_javascript_react_npm(self, tmp_path):
        """Test detection of React project with npm."""
        package_json = {
            "name": "test-app",
            "dependencies": {"react": "^18.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        (tmp_path / "package-lock.json").write_text("")  # Lock file marker

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "javascript"
        assert context.framework == "react"
        assert context.package_manager == "npm"
        assert "react" in context.additional_tags

    def test_detect_javascript_vue_yarn(self, tmp_path):
        """Test detection of Vue project with yarn."""
        package_json = {
            "name": "test-app",
            "dependencies": {"vue": "^3.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))
        (tmp_path / "yarn.lock").write_text("")

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "javascript"
        assert context.framework == "vue"
        assert context.package_manager == "yarn"
        assert "vue" in context.additional_tags

    def test_detect_javascript_nextjs(self, tmp_path):
        """Test detection of Next.js project (should add both next and react)."""
        package_json = {
            "name": "test-app",
            "dependencies": {"next": "^14.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "javascript"
        assert context.framework == "next"
        assert "next" in context.additional_tags
        assert "react" in context.additional_tags  # Next.js uses React

    def test_detect_javascript_typescript(self, tmp_path):
        """Test detection of TypeScript in dependencies."""
        package_json = {
            "name": "test-app",
            "devDependencies": {"typescript": "^5.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "javascript"
        assert "typescript" in context.additional_tags

    def test_detect_python_pyproject_fastapi(self, tmp_path):
        """Test detection of Python FastAPI project from pyproject.toml."""
        pyproject = {
            "project": {
                "name": "test-api",
                "dependencies": ["fastapi>=0.100.0", "uvicorn[standard]>=0.20.0"],
            }
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "python"
        assert context.framework == "fastapi"
        assert context.package_manager == "pip"
        assert "fastapi" in context.additional_tags

    def test_detect_python_pyproject_django_poetry(self, tmp_path):
        """Test detection of Python Django project with Poetry."""
        pyproject = {
            "tool": {
                "poetry": {
                    "name": "test-project",
                    "dependencies": {"python": "^3.9", "django": "^4.2"},
                }
            }
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "python"
        assert context.framework == "django"
        assert context.package_manager == "poetry"
        assert "django" in context.additional_tags

    def test_detect_python_pyproject_uv(self, tmp_path):
        """Test detection of Python project with uv package manager."""
        pyproject = {
            "project": {
                "name": "test-api",
                "dependencies": ["requests>=2.31.0"],
            }
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))
        (tmp_path / "uv.lock").write_text("")  # Lock file marker

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "python"
        assert context.package_manager == "uv"

    def test_detect_python_requirements_flask(self, tmp_path):
        """Test detection of Flask from requirements.txt."""
        requirements = "Flask==2.3.0\ngunicorn==21.2.0\n"
        (tmp_path / "requirements.txt").write_text(requirements)

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "python"
        assert context.framework == "flask"
        assert context.package_manager == "pip"
        assert "flask" in context.additional_tags

    def test_detect_python_setup_py(self, tmp_path):
        """Test detection from setup.py."""
        setup_py = """
from setuptools import setup

setup(
    name="test-package",
    install_requires=["django>=4.0"],
)
"""
        (tmp_path / "setup.py").write_text(setup_py)

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "python"
        assert context.framework == "django"
        assert context.package_manager == "pip"

    def test_detect_rust_cargo(self, tmp_path):
        """Test detection of Rust project from Cargo.toml."""
        cargo = {
            "package": {"name": "test-app", "version": "0.1.0"},
            "dependencies": {"actix-web": "4.0"},
        }
        (tmp_path / "Cargo.toml").write_text(tomli_w.dumps(cargo))

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "rust"
        assert context.framework == "actix-web"
        assert context.package_manager == "cargo"
        assert "actix-web" in context.additional_tags

    def test_detect_go_project(self, tmp_path):
        """Test detection of Go project from go.mod."""
        go_mod = """
module github.com/user/test

go 1.20

require github.com/gin-gonic/gin v1.9.0
"""
        (tmp_path / "go.mod").write_text(go_mod)

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "go"
        assert context.framework == "gin"
        assert context.package_manager == "go"
        assert "gin" in context.additional_tags

    def test_detect_java_maven(self, tmp_path):
        """Test detection of Java project with Maven."""
        pom_xml = '<?xml version="1.0"?><project></project>'
        (tmp_path / "pom.xml").write_text(pom_xml)

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "java"
        assert context.package_manager == "maven"
        assert "maven" in context.additional_tags

    def test_detect_java_gradle(self, tmp_path):
        """Test detection of Java project with Gradle."""
        build_gradle = "plugins { id 'java' }"
        (tmp_path / "build.gradle").write_text(build_gradle)

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language == "java"
        assert context.package_manager == "gradle"
        assert "gradle" in context.additional_tags

    def test_detect_claude_code_project(self, tmp_path):
        """Test detection of Claude Code project."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.local.json").write_text("{}")

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert "claude-code" in context.additional_tags

    def test_no_manifest_found(self, tmp_path):
        """Test detection when no manifests exist."""
        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        assert context.language is None
        assert context.framework is None
        assert context.package_manager is None
        assert context.additional_tags == set()

    def test_invalid_package_json(self, tmp_path):
        """Test handling of malformed package.json."""
        (tmp_path / "package.json").write_text("invalid json{")

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        # Should return empty context without crashing
        assert context.language is None

    def test_invalid_pyproject_toml(self, tmp_path):
        """Test handling of malformed pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("invalid = toml [[[")

        booster = ContextBooster(project_root=tmp_path)
        context = booster.detect_context()

        # Should return empty context without crashing
        assert context.language is None


class TestContextBoosterScoring:
    """Test score boosting logic."""

    def test_get_boost_language_match(self, tmp_path):
        """Test boost for language match."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["requests"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path, boost_multiplier=1.15)

        artifact = ArtifactMetadata(
            title="Python Testing Tool",
            description="A tool for Python developers",
            tags=["python", "testing"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.15

    def test_get_boost_framework_match(self, tmp_path):
        """Test boost for framework match."""
        package_json = {
            "dependencies": {"react": "^18.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        booster = ContextBooster(project_root=tmp_path)

        artifact = ArtifactMetadata(
            title="React Component Library",
            description="UI components for React",
            tags=["react", "ui"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.1  # Default multiplier

    def test_get_boost_tag_match(self, tmp_path):
        """Test boost for additional tag match."""
        package_json = {
            "devDependencies": {"typescript": "^5.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        booster = ContextBooster(project_root=tmp_path)

        artifact = ArtifactMetadata(
            title="TypeScript Utilities",
            description="Helper functions",
            tags=["typescript", "utilities"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.1

    def test_get_boost_no_match(self, tmp_path):
        """Test no boost when context doesn't match artifact."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["requests"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)

        artifact = ArtifactMetadata(
            title="Rust Library",
            description="A Rust tool",
            tags=["rust", "systems"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.0  # No boost

    def test_get_boost_no_context(self, tmp_path):
        """Test no boost when no context detected."""
        booster = ContextBooster(project_root=tmp_path)

        artifact = ArtifactMetadata(
            title="Generic Tool",
            description="A helpful tool",
            tags=["utilities"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.0

    def test_apply_boost_basic(self, tmp_path):
        """Test applying boost to base score."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["fastapi"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path, boost_multiplier=1.1)

        artifact = ArtifactMetadata(
            title="FastAPI Helper",
            description="FastAPI utilities",
            tags=["fastapi", "web"],
        )

        boosted = booster.apply_boost(artifact, base_score=80.0)
        assert boosted == 88.0  # 80 * 1.1

    def test_apply_boost_capped_at_100(self, tmp_path):
        """Test that boosted score is capped at 100."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["django"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path, boost_multiplier=1.2)

        artifact = ArtifactMetadata(
            title="Django Extension",
            description="Django tools",
            tags=["django"],
        )

        boosted = booster.apply_boost(artifact, base_score=95.0)
        assert boosted == 100.0  # Capped at 100 (95 * 1.2 = 114)

    def test_boost_multiplier_capped_at_max(self, tmp_path):
        """Test that boost multiplier is capped at 1.2."""
        booster = ContextBooster(project_root=tmp_path, boost_multiplier=1.5)
        assert booster.boost_multiplier == 1.2  # Capped

        booster2 = ContextBooster(project_root=tmp_path, boost_multiplier=1.1)
        assert booster2.boost_multiplier == 1.1  # Not capped

    def test_context_lazy_initialization(self, tmp_path):
        """Test that context is lazily initialized."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["requests"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)
        assert booster._context is None  # Not yet initialized

        # Access context property
        context = booster.context
        assert context is not None
        assert context.language == "python"

        # Should be cached now
        assert booster._context is context

    def test_get_boost_lazy_initialization(self, tmp_path):
        """Test that get_boost lazily initializes context."""
        pyproject = {
            "project": {"name": "test", "dependencies": ["flask"]},
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)
        assert booster._context is None

        artifact = ArtifactMetadata(
            title="Flask Plugin",
            description="Flask utilities",
            tags=["flask"],
        )

        boost = booster.get_boost(artifact)
        assert boost == 1.1
        assert booster._context is not None
        assert booster._context.framework == "flask"


class TestContextBoosterIntegration:
    """Integration tests for ContextBooster."""

    def test_full_workflow_react_project(self, tmp_path):
        """Test full workflow: detect React project and boost React artifacts."""
        # Setup React project
        package_json = {
            "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        booster = ContextBooster(project_root=tmp_path)

        # React artifact should be boosted
        react_artifact = ArtifactMetadata(
            title="React Hooks Collection",
            description="Custom React hooks",
            tags=["react", "hooks"],
        )
        react_score = booster.apply_boost(react_artifact, base_score=75.0)
        assert react_score == 82.5  # 75 * 1.1

        # Python artifact should not be boosted
        python_artifact = ArtifactMetadata(
            title="Python Utilities",
            description="Python helper functions",
            tags=["python"],
        )
        python_score = booster.apply_boost(python_artifact, base_score=75.0)
        assert python_score == 75.0  # No boost

    def test_multiple_artifact_evaluation(self, tmp_path):
        """Test evaluating multiple artifacts with same booster instance."""
        pyproject = {
            "project": {
                "name": "test",
                "dependencies": ["fastapi", "sqlalchemy"],
            }
        }
        (tmp_path / "pyproject.toml").write_text(tomli_w.dumps(pyproject))

        booster = ContextBooster(project_root=tmp_path)

        artifacts = [
            ArtifactMetadata(title="FastAPI Plugin", tags=["fastapi"]),
            ArtifactMetadata(title="Python Tool", tags=["python"]),
            ArtifactMetadata(title="JavaScript Utility", tags=["javascript"]),
        ]

        boosts = [booster.get_boost(a) for a in artifacts]

        assert boosts[0] == 1.1  # FastAPI match
        assert boosts[1] == 1.1  # Python match
        assert boosts[2] == 1.0  # No match

    def test_default_project_root(self):
        """Test that default project root is current directory."""
        booster = ContextBooster()
        assert booster.project_root == Path.cwd()
