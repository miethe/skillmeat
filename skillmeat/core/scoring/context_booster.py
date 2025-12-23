"""Context-aware scoring for artifacts based on project type detection."""

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set

from skillmeat.core.artifact import ArtifactMetadata

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Detected project context from manifest files."""

    language: Optional[str] = None  # "python", "javascript", "rust", etc.
    framework: Optional[str] = None  # "react", "fastapi", "django", etc.
    package_manager: Optional[str] = None  # "npm", "pip", "cargo", etc.
    additional_tags: Optional[Set[str]] = None  # Additional detected technologies

    def __post_init__(self):
        """Initialize additional_tags if not provided."""
        if self.additional_tags is None:
            self.additional_tags = set()


class ContextBooster:
    """Boost artifact scores based on project context.

    Detects project type from manifest files (package.json, pyproject.toml, etc.)
    and applies a multiplier to artifacts that match the project's tech stack.

    Args:
        project_root: Root directory to search for manifests (default: current directory)
        boost_multiplier: Score multiplier for matching artifacts (default: 1.1, max: 1.2)
    """

    def __init__(
        self, project_root: Optional[Path] = None, boost_multiplier: float = 1.1
    ):
        """Initialize context booster.

        Args:
            project_root: Root directory to search for manifests
            boost_multiplier: Multiplier for matching artifacts (capped at 1.2)
        """
        self.project_root = project_root or Path.cwd()
        self.boost_multiplier = min(boost_multiplier, 1.2)  # Cap at 1.2x
        self._context: Optional[ProjectContext] = None

    def detect_context(self) -> ProjectContext:
        """Detect project type from manifest files.

        Searches for common manifest files in project_root and extracts
        language, framework, and package manager information.

        Returns:
            ProjectContext with detected information
        """
        # Check for package.json (JavaScript/TypeScript/Node)
        package_json_path = self.project_root / "package.json"
        if package_json_path.exists():
            return self._detect_javascript_context(package_json_path)

        # Check for Python manifests
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            return self._detect_python_context_pyproject(pyproject_path)

        requirements_path = self.project_root / "requirements.txt"
        if requirements_path.exists():
            return self._detect_python_context_requirements(requirements_path)

        setup_py_path = self.project_root / "setup.py"
        if setup_py_path.exists():
            return self._detect_python_context_setup(setup_py_path)

        # Check for Rust
        cargo_path = self.project_root / "Cargo.toml"
        if cargo_path.exists():
            return self._detect_rust_context(cargo_path)

        # Check for Go
        go_mod_path = self.project_root / "go.mod"
        if go_mod_path.exists():
            return self._detect_go_context(go_mod_path)

        # Check for Java (Maven)
        pom_path = self.project_root / "pom.xml"
        if pom_path.exists():
            return ProjectContext(
                language="java", package_manager="maven", additional_tags={"maven"}
            )

        # Check for Java (Gradle)
        gradle_path = self.project_root / "build.gradle"
        if gradle_path.exists():
            return ProjectContext(
                language="java", package_manager="gradle", additional_tags={"gradle"}
            )

        # Check for Claude Code project
        claude_settings = self.project_root / ".claude" / "settings.local.json"
        if claude_settings.exists():
            context = ProjectContext(additional_tags={"claude-code"})
            logger.debug("Detected Claude Code project")
            return context

        # No manifest found
        logger.debug(f"No project manifests found in {self.project_root}")
        return ProjectContext()

    def _detect_javascript_context(self, package_json_path: Path) -> ProjectContext:
        """Detect JavaScript/TypeScript project context from package.json."""
        try:
            data = json.loads(package_json_path.read_text())
            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            framework = None
            additional_tags = set()

            # Detect framework
            if "react" in deps:
                framework = "react"
                additional_tags.add("react")
            elif "vue" in deps:
                framework = "vue"
                additional_tags.add("vue")
            elif "angular" in deps or "@angular/core" in deps:
                framework = "angular"
                additional_tags.add("angular")
            elif "express" in deps:
                framework = "express"
                additional_tags.add("express")
            elif "next" in deps:
                framework = "next"
                additional_tags.add("next")
                additional_tags.add("react")  # Next.js uses React

            # Detect TypeScript
            if "typescript" in deps:
                additional_tags.add("typescript")

            # Detect package manager
            package_manager = "npm"  # Default
            if (self.project_root / "yarn.lock").exists():
                package_manager = "yarn"
            elif (self.project_root / "pnpm-lock.yaml").exists():
                package_manager = "pnpm"
            elif (self.project_root / "package-lock.json").exists():
                package_manager = "npm"

            logger.debug(
                f"Detected JavaScript project: framework={framework}, pm={package_manager}"
            )

            return ProjectContext(
                language="javascript",
                framework=framework,
                package_manager=package_manager,
                additional_tags=additional_tags,
            )

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse package.json: {e}")
            return ProjectContext()

    def _detect_python_context_pyproject(self, pyproject_path: Path) -> ProjectContext:
        """Detect Python project context from pyproject.toml."""
        try:
            data = tomllib.loads(pyproject_path.read_text())

            framework = None
            additional_tags = set()

            # Check dependencies in various formats
            deps = []
            if "project" in data and "dependencies" in data["project"]:
                deps = data["project"]["dependencies"]
            elif "tool" in data and "poetry" in data["tool"]:
                poetry_deps = data["tool"]["poetry"].get("dependencies", {})
                deps = list(poetry_deps.keys())

            # Detect framework from dependencies
            deps_lower = [d.lower() for d in deps]
            if any("fastapi" in d for d in deps_lower):
                framework = "fastapi"
                additional_tags.add("fastapi")
            elif any("django" in d for d in deps_lower):
                framework = "django"
                additional_tags.add("django")
            elif any("flask" in d for d in deps_lower):
                framework = "flask"
                additional_tags.add("flask")

            # Detect package manager
            package_manager = "pip"
            if "tool" in data and "poetry" in data["tool"]:
                package_manager = "poetry"
            elif (self.project_root / "uv.lock").exists():
                package_manager = "uv"

            logger.debug(
                f"Detected Python project: framework={framework}, pm={package_manager}"
            )

            return ProjectContext(
                language="python",
                framework=framework,
                package_manager=package_manager,
                additional_tags=additional_tags,
            )

        except (tomllib.TOMLDecodeError, OSError) as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")
            return ProjectContext()

    def _detect_python_context_requirements(
        self, requirements_path: Path
    ) -> ProjectContext:
        """Detect Python project context from requirements.txt."""
        try:
            content = requirements_path.read_text().lower()

            framework = None
            additional_tags = set()

            if "fastapi" in content:
                framework = "fastapi"
                additional_tags.add("fastapi")
            elif "django" in content:
                framework = "django"
                additional_tags.add("django")
            elif "flask" in content:
                framework = "flask"
                additional_tags.add("flask")

            logger.debug(f"Detected Python project from requirements.txt: {framework}")

            return ProjectContext(
                language="python",
                framework=framework,
                package_manager="pip",
                additional_tags=additional_tags,
            )

        except OSError as e:
            logger.warning(f"Failed to read requirements.txt: {e}")
            return ProjectContext()

    def _detect_python_context_setup(self, setup_py_path: Path) -> ProjectContext:
        """Detect Python project context from setup.py."""
        try:
            content = setup_py_path.read_text().lower()

            framework = None
            additional_tags = set()

            if "fastapi" in content:
                framework = "fastapi"
                additional_tags.add("fastapi")
            elif "django" in content:
                framework = "django"
                additional_tags.add("django")
            elif "flask" in content:
                framework = "flask"
                additional_tags.add("flask")

            logger.debug(f"Detected Python project from setup.py: {framework}")

            return ProjectContext(
                language="python",
                framework=framework,
                package_manager="pip",
                additional_tags=additional_tags,
            )

        except OSError as e:
            logger.warning(f"Failed to read setup.py: {e}")
            return ProjectContext()

    def _detect_rust_context(self, cargo_path: Path) -> ProjectContext:
        """Detect Rust project context from Cargo.toml."""
        try:
            data = tomllib.loads(cargo_path.read_text())

            framework = None
            additional_tags = set()

            # Check dependencies
            deps = data.get("dependencies", {})
            if "actix-web" in deps:
                framework = "actix-web"
                additional_tags.add("actix-web")
            elif "rocket" in deps:
                framework = "rocket"
                additional_tags.add("rocket")

            logger.debug(f"Detected Rust project: framework={framework}")

            return ProjectContext(
                language="rust",
                framework=framework,
                package_manager="cargo",
                additional_tags=additional_tags,
            )

        except (tomllib.TOMLDecodeError, OSError) as e:
            logger.warning(f"Failed to parse Cargo.toml: {e}")
            return ProjectContext()

    def _detect_go_context(self, go_mod_path: Path) -> ProjectContext:
        """Detect Go project context from go.mod."""
        try:
            content = go_mod_path.read_text().lower()

            framework = None
            additional_tags = set()

            if "gin-gonic/gin" in content:
                framework = "gin"
                additional_tags.add("gin")
            elif "echo" in content:
                framework = "echo"
                additional_tags.add("echo")

            logger.debug(f"Detected Go project: framework={framework}")

            return ProjectContext(
                language="go",
                framework=framework,
                package_manager="go",
                additional_tags=additional_tags,
            )

        except OSError as e:
            logger.warning(f"Failed to read go.mod: {e}")
            return ProjectContext()

    def get_boost(self, artifact: ArtifactMetadata) -> float:
        """Get boost multiplier for artifact based on project context.

        Args:
            artifact: Artifact metadata to check for matches

        Returns:
            Boost multiplier (1.0 = no boost, 1.1-1.2 = boosted)
        """
        # Lazy initialization of context
        if self._context is None:
            self._context = self.detect_context()

        context = self._context

        # No context detected → no boost
        if (
            not context.language
            and not context.framework
            and not context.additional_tags
        ):
            return 1.0

        # Build searchable text from artifact
        artifact_text_parts = [
            artifact.title or "",
            artifact.description or "",
            " ".join(artifact.tags or []),
        ]
        artifact_text = " ".join(artifact_text_parts).lower()

        # Check for language match
        if context.language and context.language.lower() in artifact_text:
            logger.debug(
                f"Boosting {artifact.title} - language match: {context.language}"
            )
            return self.boost_multiplier

        # Check for framework match
        if context.framework and context.framework.lower() in artifact_text:
            logger.debug(
                f"Boosting {artifact.title} - framework match: {context.framework}"
            )
            return self.boost_multiplier

        # Check for additional tags match
        if context.additional_tags:
            for tag in context.additional_tags:
                if tag.lower() in artifact_text:
                    logger.debug(f"Boosting {artifact.title} - tag match: {tag}")
                    return self.boost_multiplier

        return 1.0

    def apply_boost(self, artifact: ArtifactMetadata, base_score: float) -> float:
        """Apply context boost to base score.

        Args:
            artifact: Artifact to boost
            base_score: Base score before context boost

        Returns:
            Boosted score (capped at 100)
        """
        boost = self.get_boost(artifact)
        boosted_score = base_score * boost
        return min(100.0, boosted_score)

    @property
    def context(self) -> ProjectContext:
        """Get current project context (lazy initialization)."""
        if self._context is None:
            self._context = self.detect_context()
        return self._context
