"""Search functionality for SkillMeat collections.

This module provides metadata and content search across artifacts in a collection,
with optional ripgrep acceleration for fast content search.
"""

import hashlib
import json
import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.artifact import ArtifactType
from skillmeat.models import (
    ArtifactFingerprint,
    DuplicatePair,
    SearchCacheEntry,
    SearchMatch,
    SearchResult,
)
from skillmeat.utils.metadata import extract_artifact_metadata, find_metadata_file


# Maximum file size for content search (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Binary file detection patterns
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".a",
}

# Files/directories to skip during search
IGNORE_PATTERNS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    "*.egg-info",
}


@dataclass
class _ContentMatch:
    """Internal representation of a content match."""

    file_path: Path
    line_number: int
    line_content: str
    match_count: int = 1


class SearchManager:
    """Manages artifact search across collections."""

    def __init__(self, collection_mgr=None):
        """Initialize search manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
        """
        if collection_mgr is None:
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr
        self._project_cache: Dict[str, SearchCacheEntry] = {}

    def search_collection(
        self,
        query: str,
        collection_name: Optional[str] = None,
        search_type: str = "both",
        artifact_types: Optional[List[ArtifactType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> SearchResult:
        """Search artifacts in collection.

        Args:
            query: Search query string
            collection_name: Collection to search (uses active if None)
            search_type: "metadata", "content", or "both"
            artifact_types: Filter by artifact types (None = all types)
            tags: Filter by tags (None = no tag filtering)
            limit: Maximum number of results to return

        Returns:
            SearchResult with ranked matches

        Raises:
            ValueError: Invalid search_type or collection not found
        """
        start_time = time.time()

        # Validate search_type
        valid_types = {"metadata", "content", "both"}
        if search_type not in valid_types:
            raise ValueError(
                f"Invalid search_type '{search_type}'. Must be one of {valid_types}"
            )

        # Load collection
        try:
            collection = self.collection_mgr.load_collection(collection_name)
        except Exception as e:
            raise ValueError(f"Failed to load collection: {e}")

        # Get artifacts to search
        artifacts = collection.artifacts

        # Filter by artifact type if specified
        if artifact_types:
            artifacts = [a for a in artifacts if a.type in artifact_types]

        # Filter by tags if specified
        if tags:
            artifacts = [a for a in artifacts if any(tag in a.tags for tag in tags)]

        # If no artifacts, return empty result
        if not artifacts:
            return SearchResult(
                query=query,
                matches=[],
                total_count=0,
                search_time=time.time() - start_time,
                used_ripgrep=False,
                search_type=search_type,
            )

        # Perform search based on type
        all_matches = []
        used_ripgrep = False

        if search_type in ("metadata", "both"):
            metadata_matches = self._search_metadata(query, artifacts, collection)
            all_matches.extend(metadata_matches)

        if search_type in ("content", "both"):
            content_matches, rg_used = self._search_content(
                query, artifacts, collection
            )
            all_matches.extend(content_matches)
            used_ripgrep = rg_used

        # Rank and sort matches
        all_matches = self._rank_matches(query, all_matches)

        # Limit results
        if limit > 0:
            all_matches = all_matches[:limit]

        search_time = time.time() - start_time

        return SearchResult(
            query=query,
            matches=all_matches,
            total_count=len(all_matches),
            search_time=search_time,
            used_ripgrep=used_ripgrep,
            search_type=search_type,
        )

    def _search_metadata(
        self, query: str, artifacts: List, collection
    ) -> List[SearchMatch]:
        """Search artifact metadata (YAML frontmatter).

        Args:
            query: Search query
            artifacts: List of Artifact objects to search
            collection: Collection object

        Returns:
            List of SearchMatch objects for metadata matches
        """
        matches = []
        query_lower = query.lower()

        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )

        for artifact in artifacts:
            artifact_path = collection_path / artifact.path

            # Extract metadata
            try:
                metadata = extract_artifact_metadata(artifact_path, artifact.type)
            except Exception as e:
                logging.debug(f"Failed to extract metadata for {artifact.name}: {e}")
                continue

            # Search metadata fields
            score = 0.0
            match_contexts = []

            # Title match (highest weight)
            if metadata.title and query_lower in metadata.title.lower():
                score += 10.0
                match_contexts.append(f"Title: {metadata.title}")

            # Description match
            if metadata.description and query_lower in metadata.description.lower():
                score += 5.0
                match_contexts.append(f"Description: {metadata.description[:100]}")

            # Tags match (high weight)
            if metadata.tags:
                for tag in metadata.tags:
                    if query_lower in tag.lower():
                        score += 8.0
                        match_contexts.append(f"Tag: {tag}")

            # Author match
            if metadata.author and query_lower in metadata.author.lower():
                score += 3.0
                match_contexts.append(f"Author: {metadata.author}")

            # License match
            if metadata.license and query_lower in metadata.license.lower():
                score += 2.0
                match_contexts.append(f"License: {metadata.license}")

            # If any metadata match, create SearchMatch
            if score > 0:
                context = " | ".join(match_contexts[:3])  # Limit context to 3 items
                matches.append(
                    SearchMatch(
                        artifact_name=artifact.name,
                        artifact_type=artifact.type.value,
                        score=score,
                        match_type="metadata",
                        context=context,
                        line_number=None,
                        metadata=metadata.to_dict(),
                    )
                )

        return matches

    def _search_content(
        self, query: str, artifacts: List, collection
    ) -> tuple[List[SearchMatch], bool]:
        """Search artifact file contents.

        Tries ripgrep first, falls back to Python if not available.

        Args:
            query: Search query
            artifacts: List of Artifact objects to search
            collection: Collection object

        Returns:
            Tuple of (list of SearchMatch objects, whether ripgrep was used)
        """
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )

        # Get artifact paths
        artifact_paths = []
        artifact_map = {}  # Map path to artifact
        for artifact in artifacts:
            artifact_path = collection_path / artifact.path
            if artifact_path.exists():
                artifact_paths.append(artifact_path)
                artifact_map[artifact_path] = artifact

        if not artifact_paths:
            return [], False

        # Try ripgrep first
        try:
            content_matches = self._search_with_ripgrep(query, artifact_paths)
            used_ripgrep = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Ripgrep not available or timed out, use Python fallback
            content_matches = self._search_with_python(query, artifact_paths)
            used_ripgrep = False

        # Convert content matches to SearchMatch objects
        search_matches = []
        for match in content_matches:
            # Find which artifact this match belongs to
            artifact = None
            for artifact_path, art in artifact_map.items():
                if self._is_path_in_artifact(match.file_path, artifact_path):
                    artifact = art
                    break

            if artifact is None:
                continue

            # Calculate score based on match count
            score = float(match.match_count)

            # Create context from line content
            context = match.line_content.strip()
            if len(context) > 200:
                context = context[:200] + "..."

            # Extract metadata for match
            try:
                artifact_path = collection_path / artifact.path
                metadata = extract_artifact_metadata(artifact_path, artifact.type)
                metadata_dict = metadata.to_dict()
            except Exception:
                metadata_dict = {}

            search_matches.append(
                SearchMatch(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    score=score,
                    match_type="content",
                    context=context,
                    line_number=match.line_number,
                    metadata=metadata_dict,
                )
            )

        return search_matches, used_ripgrep

    def _search_with_ripgrep(
        self, query: str, paths: List[Path]
    ) -> List[_ContentMatch]:
        """Use ripgrep for fast content search.

        Args:
            query: Search query
            paths: List of paths to search

        Returns:
            List of _ContentMatch objects

        Raises:
            FileNotFoundError: ripgrep not installed
            subprocess.TimeoutExpired: Search exceeded timeout
        """
        # Build ripgrep command
        cmd = [
            "rg",
            "--json",  # JSON output for parsing
            "--ignore-case",  # Case-insensitive
            "--max-filesize",
            str(MAX_FILE_SIZE),  # Skip large files
        ]

        # Add ignore patterns
        for pattern in IGNORE_PATTERNS:
            cmd.extend(["--glob", f"!{pattern}"])

        # Add query and paths
        cmd.append(query)
        cmd.extend([str(p) for p in paths])

        # Run ripgrep with timeout
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )
        except FileNotFoundError:
            # ripgrep not installed
            raise

        # Parse JSON output
        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    path_data = match_data.get("path", {})
                    line_number = match_data.get("line_number", 0)
                    lines_data = match_data.get("lines", {})

                    file_path = Path(path_data.get("text", ""))
                    line_content = lines_data.get("text", "")

                    # Count matches in this line
                    match_count = line_content.lower().count(query.lower())

                    matches.append(
                        _ContentMatch(
                            file_path=file_path,
                            line_number=line_number,
                            line_content=line_content,
                            match_count=match_count,
                        )
                    )
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue

        return matches

    def _search_with_python(self, query: str, paths: List[Path]) -> List[_ContentMatch]:
        """Pure Python content search (slower but works everywhere).

        Args:
            query: Search query
            paths: List of paths to search

        Returns:
            List of _ContentMatch objects
        """
        matches = []
        query_lower = query.lower()

        for path in paths:
            # Get all files in path
            if path.is_file():
                files = [path]
            else:
                files = self._get_searchable_files(path)

            # Search each file
            for file_path in files:
                # Skip if too large
                try:
                    if file_path.stat().st_size > MAX_FILE_SIZE:
                        continue
                except (OSError, IOError):
                    continue

                # Skip binary files
                if self._is_binary_file(file_path):
                    continue

                # Search file content
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if query_lower in line.lower():
                                match_count = line.lower().count(query_lower)
                                matches.append(
                                    _ContentMatch(
                                        file_path=file_path,
                                        line_number=line_num,
                                        line_content=line,
                                        match_count=match_count,
                                    )
                                )
                except (IOError, OSError, UnicodeDecodeError) as e:
                    # Skip files we can't read
                    logging.debug(f"Skipping file {file_path}: {e}")
                    continue

        return matches

    def _get_searchable_files(self, root_path: Path) -> List[Path]:
        """Get all searchable files in a directory tree.

        Args:
            root_path: Root directory to search

        Returns:
            List of file paths to search
        """
        searchable_files = []

        try:
            for path in root_path.rglob("*"):
                # Skip directories
                if not path.is_file():
                    continue

                # Skip ignored patterns
                if self._should_ignore(path):
                    continue

                searchable_files.append(path)
        except (OSError, IOError) as e:
            logging.debug(f"Error walking directory {root_path}: {e}")

        return searchable_files

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        # Check if any part of the path matches ignore patterns
        parts = path.parts
        for part in parts:
            for pattern in IGNORE_PATTERNS:
                if "*" in pattern:
                    # Glob pattern matching
                    if path.match(pattern):
                        return True
                else:
                    # Exact match
                    if part == pattern:
                        return True
        return False

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary.

        Args:
            file_path: Path to file

        Returns:
            True if file is binary
        """
        # Check extension first
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            return True

        # Read first 8KB and check for null bytes
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return True
        except (IOError, OSError):
            # If we can't read, assume binary
            return True

        return False

    def _is_path_in_artifact(self, file_path: Path, artifact_path: Path) -> bool:
        """Check if file is part of an artifact.

        Args:
            file_path: Path to file
            artifact_path: Path to artifact

        Returns:
            True if file is in artifact
        """
        try:
            # Check if file_path is relative to artifact_path
            file_path.resolve().relative_to(artifact_path.resolve())
            return True
        except ValueError:
            # Not relative
            return False

    def _rank_matches(
        self, query: str, matches: List[SearchMatch]
    ) -> List[SearchMatch]:
        """Rank and sort search matches by relevance.

        Args:
            query: Original search query
            matches: List of SearchMatch objects

        Returns:
            Sorted list of SearchMatch objects
        """
        query_lower = query.lower()

        for match in matches:
            # Start with base score
            score = match.score

            # Boost exact matches
            if query_lower == match.context.lower():
                score *= 2.0

            # Boost if query appears in artifact name
            if query_lower in match.artifact_name.lower():
                score += 5.0

            # Normalize by content length (prefer concise matches)
            if match.context:
                # Avoid division by zero
                length_factor = max(len(match.context) / 1000.0, 0.1)
                score = score / length_factor

            # Update match score
            match.score = score

        # Sort by score (descending)
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches

    # ========================================================================
    # Cross-Project Search Methods (P2-002)
    # ========================================================================

    def search_projects(
        self,
        query: str,
        project_paths: Optional[List[Path]] = None,
        search_type: str = "both",
        artifact_types: Optional[List[ArtifactType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        use_cache: bool = True,
    ) -> SearchResult:
        """Search across multiple project directories.

        Args:
            query: Search query string
            project_paths: Explicit project paths (None = discover from config)
            search_type: "metadata", "content", or "both"
            artifact_types: Filter by artifact types
            tags: Filter by tags
            limit: Maximum results
            use_cache: Use cached index if available

        Returns:
            SearchResult with project_path in each match

        Raises:
            ValueError: Invalid search_type
        """
        start_time = time.time()

        # Validate search_type
        valid_types = {"metadata", "content", "both"}
        if search_type not in valid_types:
            raise ValueError(
                f"Invalid search_type '{search_type}'. Must be one of {valid_types}"
            )

        # Step 1: Discover projects
        if project_paths is None:
            project_paths = self._discover_projects()

        if not project_paths:
            # No projects found
            return SearchResult(
                query=query,
                matches=[],
                total_count=0,
                search_time=time.time() - start_time,
                used_ripgrep=False,
                search_type=search_type,
            )

        # Step 2: Build/retrieve index
        cache_key = self._compute_cache_key(project_paths)

        if use_cache:
            cached_index = self._get_cached_index(cache_key, project_paths)
            if cached_index:
                project_indexes = cached_index
            else:
                project_indexes = self._build_project_index(project_paths)
                self._cache_index(cache_key, project_indexes)
        else:
            project_indexes = self._build_project_index(project_paths)

        # Step 3: Search across all projects
        all_matches = []
        used_ripgrep = False

        for project_index in project_indexes:
            project_path = project_index["project_path"]
            artifacts = project_index["artifacts"]

            # Search metadata
            if search_type in ("metadata", "both"):
                metadata_matches = self._search_project_metadata(
                    query, artifacts, project_path
                )
                all_matches.extend(metadata_matches)

            # Search content
            if search_type in ("content", "both"):
                content_matches, rg_used = self._search_project_content(
                    query, artifacts, project_path
                )
                all_matches.extend(content_matches)
                used_ripgrep = used_ripgrep or rg_used

        # Step 4: Rank and filter
        all_matches = self._rank_matches(query, all_matches)

        # Filter by type/tags if specified
        if artifact_types:
            all_matches = [
                m
                for m in all_matches
                if m.artifact_type in [t.value for t in artifact_types]
            ]
        if tags:
            all_matches = [
                m
                for m in all_matches
                if any(tag in m.metadata.get("tags", []) for tag in tags)
            ]

        # Limit results
        if limit > 0:
            all_matches = all_matches[:limit]

        search_time = time.time() - start_time

        return SearchResult(
            query=query,
            matches=all_matches,
            total_count=len(all_matches),
            search_time=search_time,
            used_ripgrep=used_ripgrep,
            search_type=search_type,
        )

    def _discover_projects(self, roots: Optional[List[Path]] = None) -> List[Path]:
        """Discover all .claude/ directories under roots.

        Args:
            roots: List of root paths to search (uses config if None)

        Returns:
            List of paths to .claude/ directories
        """
        if roots is None:
            # Get from config
            configured_roots = self.collection_mgr.config.get(
                "search.project-roots", []
            )
            if not configured_roots:
                # Default to no roots if not configured
                return []
            roots = [Path(r).expanduser() for r in configured_roots]

        max_depth = self.collection_mgr.config.get("search.max-depth", 3)
        exclude_patterns = self.collection_mgr.config.get(
            "search.exclude-dirs",
            ["node_modules", ".venv", "venv", ".git", "__pycache__"],
        )

        projects = []
        for root in roots:
            if not root.exists():
                logging.warning(f"Project root does not exist: {root}")
                continue

            # Find all .claude directories
            try:
                for project_path in self._walk_directories(
                    root, max_depth, exclude_patterns
                ):
                    claude_dir = project_path / ".claude"
                    if claude_dir.is_dir():
                        projects.append(claude_dir)
            except (OSError, IOError) as e:
                logging.warning(f"Error walking directory {root}: {e}")
                continue

        return projects

    def _walk_directories(
        self, root: Path, max_depth: int, exclude_patterns: List[str]
    ) -> List[Path]:
        """Walk directories up to max_depth, excluding patterns.

        Args:
            root: Root directory to walk
            max_depth: Maximum recursion depth
            exclude_patterns: Directory names to exclude

        Returns:
            List of directory paths to check
        """
        directories = [root]
        exclude_set = set(exclude_patterns)

        def should_exclude(path: Path) -> bool:
            """Check if path should be excluded."""
            return path.name in exclude_set

        def walk_level(current_dir: Path, depth: int) -> None:
            """Recursively walk directories."""
            if depth > max_depth:
                return

            try:
                for entry in current_dir.iterdir():
                    if not entry.is_dir():
                        continue

                    if should_exclude(entry):
                        continue

                    directories.append(entry)
                    walk_level(entry, depth + 1)
            except (OSError, IOError, PermissionError) as e:
                logging.debug(f"Cannot access {current_dir}: {e}")

        walk_level(root, 1)
        return directories

    def _build_project_index(self, project_paths: List[Path]) -> List[Dict[str, any]]:
        """Build searchable index from project .claude/ directories.

        Args:
            project_paths: List of .claude/ directory paths

        Returns:
            List of project index dicts
        """
        indexes = []

        for project_path in project_paths:
            # Check for skills/ directory
            skills_dir = project_path / "skills"
            artifacts = []

            if skills_dir.exists() and skills_dir.is_dir():
                try:
                    for skill_dir in skills_dir.iterdir():
                        if not skill_dir.is_dir():
                            continue

                        # Validate skill
                        from skillmeat.utils.validator import ArtifactValidator

                        result = ArtifactValidator.validate_skill(skill_dir)
                        if not result.is_valid:
                            continue

                        # Extract metadata
                        try:
                            metadata = extract_artifact_metadata(
                                skill_dir, ArtifactType.SKILL
                            )
                        except Exception as e:
                            logging.debug(
                                f"Failed to extract metadata for {skill_dir.name}: {e}"
                            )
                            # Create default metadata
                            from skillmeat.utils.metadata import ArtifactMetadata

                            metadata = ArtifactMetadata()

                        artifacts.append(
                            {
                                "name": skill_dir.name,
                                "type": ArtifactType.SKILL,
                                "path": skill_dir,
                                "metadata": metadata,
                            }
                        )
                except (OSError, IOError) as e:
                    logging.warning(f"Error reading skills directory {skills_dir}: {e}")

            # Get directory mtime for cache invalidation
            try:
                mtime = project_path.stat().st_mtime
            except (OSError, IOError):
                mtime = 0.0

            indexes.append(
                {
                    "project_path": project_path,
                    "artifacts": artifacts,
                    "last_modified": mtime,
                }
            )

        return indexes

    def _search_project_metadata(
        self, query: str, artifacts: List[Dict], project_path: Path
    ) -> List[SearchMatch]:
        """Search project artifact metadata.

        Args:
            query: Search query
            artifacts: List of artifact dicts
            project_path: Path to .claude/ directory

        Returns:
            List of SearchMatch objects
        """
        matches = []
        query_lower = query.lower()

        for artifact in artifacts:
            metadata = artifact["metadata"]

            # Search metadata fields
            score = 0.0
            match_contexts = []

            # Title match (highest weight)
            if metadata.title and query_lower in metadata.title.lower():
                score += 10.0
                match_contexts.append(f"Title: {metadata.title}")

            # Description match
            if metadata.description and query_lower in metadata.description.lower():
                score += 5.0
                match_contexts.append(f"Description: {metadata.description[:100]}")

            # Tags match (high weight)
            if metadata.tags:
                for tag in metadata.tags:
                    if query_lower in tag.lower():
                        score += 8.0
                        match_contexts.append(f"Tag: {tag}")

            # Author match
            if metadata.author and query_lower in metadata.author.lower():
                score += 3.0
                match_contexts.append(f"Author: {metadata.author}")

            # License match
            if metadata.license and query_lower in metadata.license.lower():
                score += 2.0
                match_contexts.append(f"License: {metadata.license}")

            # If any metadata match, create SearchMatch
            if score > 0:
                context = " | ".join(match_contexts[:3])
                matches.append(
                    SearchMatch(
                        artifact_name=artifact["name"],
                        artifact_type=artifact["type"].value,
                        score=score,
                        match_type="metadata",
                        context=context,
                        line_number=None,
                        metadata=metadata.to_dict(),
                        project_path=project_path,
                    )
                )

        return matches

    def _search_project_content(
        self, query: str, artifacts: List[Dict], project_path: Path
    ) -> tuple[List[SearchMatch], bool]:
        """Search project artifact file contents.

        Args:
            query: Search query
            artifacts: List of artifact dicts
            project_path: Path to .claude/ directory

        Returns:
            Tuple of (list of SearchMatch objects, whether ripgrep was used)
        """
        # Get artifact paths
        artifact_paths = []
        artifact_map = {}
        for artifact in artifacts:
            artifact_path = artifact["path"]
            if artifact_path.exists():
                artifact_paths.append(artifact_path)
                artifact_map[artifact_path] = artifact

        if not artifact_paths:
            return [], False

        # Try ripgrep first
        try:
            content_matches = self._search_with_ripgrep(query, artifact_paths)
            used_ripgrep = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Ripgrep not available or timed out, use Python fallback
            content_matches = self._search_with_python(query, artifact_paths)
            used_ripgrep = False

        # Convert content matches to SearchMatch objects
        search_matches = []
        for match in content_matches:
            # Find which artifact this match belongs to
            artifact = None
            for artifact_path, art in artifact_map.items():
                if self._is_path_in_artifact(match.file_path, artifact_path):
                    artifact = art
                    break

            if artifact is None:
                continue

            # Calculate score based on match count
            score = float(match.match_count)

            # Create context from line content
            context = match.line_content.strip()
            if len(context) > 200:
                context = context[:200] + "..."

            # Use artifact metadata
            metadata_dict = artifact["metadata"].to_dict()

            search_matches.append(
                SearchMatch(
                    artifact_name=artifact["name"],
                    artifact_type=artifact["type"].value,
                    score=score,
                    match_type="content",
                    context=context,
                    line_number=match.line_number,
                    metadata=metadata_dict,
                    project_path=project_path,
                )
            )

        return search_matches, used_ripgrep

    def _compute_cache_key(self, project_paths: List[Path]) -> str:
        """Generate cache key from project paths.

        Args:
            project_paths: List of project paths

        Returns:
            MD5 hash of sorted paths
        """
        # Sort for consistent keys
        sorted_paths = sorted([str(p) for p in project_paths])
        combined = "".join(sorted_paths)
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_cached_index(
        self, cache_key: str, project_paths: List[Path]
    ) -> Optional[List[Dict[str, any]]]:
        """Retrieve cached index if valid.

        Args:
            cache_key: Cache key to lookup
            project_paths: List of project paths (for mtime validation)

        Returns:
            Cached index if valid, None otherwise
        """
        entry = self._project_cache.get(cache_key)
        if entry is None:
            return None

        if entry.is_expired():
            del self._project_cache[cache_key]
            return None

        # Check if any project directories were modified
        for project_index in entry.index:
            project_path = project_index["project_path"]
            cached_mtime = project_index["last_modified"]

            try:
                current_mtime = project_path.stat().st_mtime
                if current_mtime > cached_mtime:
                    # Directory modified, invalidate cache
                    del self._project_cache[cache_key]
                    return None
            except (OSError, IOError):
                # Directory no longer exists
                del self._project_cache[cache_key]
                return None

        return entry.index

    def _cache_index(self, cache_key: str, index: List[Dict[str, any]]) -> None:
        """Store index in cache.

        Args:
            cache_key: Cache key
            index: Index to cache
        """
        ttl = self.collection_mgr.config.get("search.cache-ttl", 60.0)
        self._project_cache[cache_key] = SearchCacheEntry(
            index=index, created_at=time.time(), ttl=ttl
        )

    def find_duplicates(
        self,
        threshold: float = 0.85,
        project_paths: Optional[List[Path]] = None,
        use_cache: bool = True,
    ) -> List[DuplicatePair]:
        """Find duplicate artifacts across projects.

        Uses multi-factor similarity comparison based on:
        - Content hash (50% weight): SHA256 of all file contents
        - Structure hash (20% weight): File tree structure
        - Metadata (20% weight): Title, description, tags
        - File count (10% weight): Number of files similarity

        Args:
            threshold: Minimum similarity score (0.0 to 1.0, default: 0.85)
            project_paths: Explicit project paths (None = discover from config)
            use_cache: Use cached index if available (default: True)

        Returns:
            List of DuplicatePair objects sorted by similarity (descending)

        Raises:
            ValueError: If threshold is not between 0.0 and 1.0
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        # Step 1: Discover projects (reuse from P2-002)
        if project_paths is None:
            project_paths = self._discover_projects()

        if not project_paths:
            return []

        # Step 2: Build/retrieve index (reuse from P2-002)
        cache_key = self._compute_cache_key(project_paths)
        if use_cache:
            cached_index = self._get_cached_index(cache_key, project_paths)
            if cached_index:
                project_indexes = cached_index
            else:
                project_indexes = self._build_project_index(project_paths)
                self._cache_index(cache_key, project_indexes)
        else:
            project_indexes = self._build_project_index(project_paths)

        # Step 3: Extract all artifacts
        all_artifacts = []
        for project_index in project_indexes:
            all_artifacts.extend(project_index["artifacts"])

        if len(all_artifacts) < 2:
            # Need at least 2 artifacts to find duplicates
            return []

        # Step 4: Compute fingerprints
        fingerprints = []
        for artifact in all_artifacts:
            try:
                fp = self._compute_fingerprint(artifact)
                fingerprints.append(fp)
            except Exception as e:
                logging.debug(
                    f"Failed to compute fingerprint for {artifact['name']}: {e}"
                )
                continue

        if len(fingerprints) < 2:
            return []

        # Step 5: Compare all pairs
        duplicates = []
        for i in range(len(fingerprints)):
            for j in range(i + 1, len(fingerprints)):
                fp1 = fingerprints[i]
                fp2 = fingerprints[j]

                # Skip same artifact (by path)
                if fp1.artifact_path == fp2.artifact_path:
                    continue

                # Compute similarity
                similarity = fp1.compute_similarity(fp2)

                if similarity >= threshold:
                    match_reasons = self._get_match_reasons(fp1, fp2)
                    duplicates.append(
                        DuplicatePair(
                            artifact1_path=fp1.artifact_path,
                            artifact1_name=fp1.artifact_name,
                            artifact2_path=fp2.artifact_path,
                            artifact2_name=fp2.artifact_name,
                            similarity_score=similarity,
                            match_reasons=match_reasons,
                        )
                    )

        # Step 6: Sort by similarity (descending)
        duplicates.sort(key=lambda d: d.similarity_score, reverse=True)

        return duplicates

    def _compute_fingerprint(self, artifact: Dict) -> ArtifactFingerprint:
        """Compute fingerprint for duplicate detection.

        Args:
            artifact: Artifact dict from project index with keys:
                - name: str
                - type: ArtifactType
                - path: Path
                - metadata: ArtifactMetadata

        Returns:
            ArtifactFingerprint with computed hashes

        Raises:
            OSError: If artifact path is not accessible
        """
        artifact_path = artifact["path"]
        metadata = artifact["metadata"]

        # Compute content hash (SHA256 of all files)
        content_hash = self._hash_artifact_contents(artifact_path)

        # Compute structure hash (file tree structure)
        structure_hash = self._hash_artifact_structure(artifact_path)

        # Compute metadata hash
        metadata_str = f"{metadata.title or ''}{metadata.description or ''}"
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()

        # Get file stats
        file_count = 0
        total_size = 0
        try:
            for file_path in artifact_path.rglob("*"):
                if file_path.is_file() and not self._should_ignore_file(file_path):
                    file_count += 1
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        # Skip files we can't stat
                        pass
        except (OSError, IOError) as e:
            logging.debug(f"Error scanning artifact {artifact['name']}: {e}")

        return ArtifactFingerprint(
            artifact_path=artifact_path,
            artifact_name=artifact["name"],
            artifact_type=artifact["type"].value,
            content_hash=content_hash,
            metadata_hash=metadata_hash,
            structure_hash=structure_hash,
            title=metadata.title,
            description=metadata.description,
            tags=metadata.tags or [],
            file_count=file_count,
            total_size=total_size,
        )

    def _hash_artifact_contents(self, artifact_path: Path) -> str:
        """Hash all file contents in artifact.

        Args:
            artifact_path: Path to artifact directory

        Returns:
            SHA256 hash of concatenated file contents

        Note:
            Skips binary files and files larger than MAX_FILE_SIZE.
            Returns consistent hash for same content even if file order varies
            (files are sorted before hashing).
        """
        hasher = hashlib.sha256()

        # Get all files, sorted for consistency
        try:
            files = sorted(artifact_path.rglob("*"))
        except (OSError, IOError):
            # If we can't list files, return empty hash
            return hasher.hexdigest()

        for file_path in files:
            if not file_path.is_file():
                continue

            # Skip ignored files
            if self._should_ignore_file(file_path):
                continue

            # Skip binary files
            if self._is_binary_file(file_path):
                continue

            # Skip large files
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    logging.debug(f"Skipping large file: {file_path}")
                    continue
            except (OSError, IOError):
                continue

            # Hash file contents
            try:
                with open(file_path, "rb") as f:
                    hasher.update(f.read())
            except (OSError, IOError, PermissionError):
                # Skip unreadable files
                logging.debug(f"Cannot read file: {file_path}")
                continue

        return hasher.hexdigest()

    def _hash_artifact_structure(self, artifact_path: Path) -> str:
        """Hash artifact file tree structure.

        Args:
            artifact_path: Path to artifact directory

        Returns:
            SHA256 hash of file tree (paths only, not contents)

        Note:
            This hash represents the structure (file/directory names and hierarchy)
            but not the content. Useful for detecting artifacts with same structure
            but different content.
        """
        hasher = hashlib.sha256()

        # Get all files and directories, sorted for consistency
        try:
            paths = sorted(artifact_path.rglob("*"))
        except (OSError, IOError):
            return hasher.hexdigest()

        for path in paths:
            if self._should_ignore_file(path):
                continue

            # Use relative path for consistency
            try:
                rel_path = path.relative_to(artifact_path)
                hasher.update(str(rel_path).encode())
            except ValueError:
                # Path is not relative to artifact_path
                continue

        return hasher.hexdigest()

    def _get_match_reasons(
        self, fp1: ArtifactFingerprint, fp2: ArtifactFingerprint
    ) -> List[str]:
        """Determine why two fingerprints are similar.

        Args:
            fp1: First fingerprint
            fp2: Second fingerprint

        Returns:
            List of match reasons (e.g., ["exact_content", "same_structure"])

        Note:
            Possible reasons:
            - "exact_content": Content hashes match exactly
            - "same_structure": File tree structure matches
            - "exact_metadata": Metadata hashes match
            - "similar_tags": Tags have >50% Jaccard similarity
            - "same_title": Titles match (case-insensitive)
        """
        reasons = []

        # Exact content match
        if fp1.content_hash == fp2.content_hash:
            reasons.append("exact_content")

        # Structure match
        if fp1.structure_hash == fp2.structure_hash:
            reasons.append("same_structure")

        # Metadata hash match
        if fp1.metadata_hash == fp2.metadata_hash:
            reasons.append("exact_metadata")

        # Tag similarity (Jaccard >= 0.5)
        if fp1.tags and fp2.tags:
            self_tags = set(t.lower() for t in fp1.tags)
            other_tags = set(t.lower() for t in fp2.tags)
            if self_tags or other_tags:
                jaccard = len(self_tags & other_tags) / len(self_tags | other_tags)
                if jaccard >= 0.5:
                    reasons.append("similar_tags")

        # Title match
        if fp1.title and fp2.title and fp1.title.lower() == fp2.title.lower():
            reasons.append("same_title")

        return reasons

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored during hashing.

        Args:
            file_path: Path to check

        Returns:
            True if file should be ignored

        Note:
            Ignores files in IGNORE_PATTERNS directories and common
            temporary/build artifacts.
        """
        # Check if any parent matches ignore patterns
        for pattern in IGNORE_PATTERNS:
            # Handle glob patterns
            if "*" in pattern:
                if file_path.match(pattern):
                    return True
            # Handle directory names
            else:
                for parent in file_path.parents:
                    if parent.name == pattern:
                        return True
                if file_path.name == pattern:
                    return True

        return False

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary.

        Args:
            file_path: Path to check

        Returns:
            True if file appears to be binary

        Note:
            Uses extension-based detection and null-byte check for
            files without known binary extensions.
        """
        # Check extension
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            return True

        # For unknown extensions, check for null bytes in first 8KB
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return True
        except (OSError, IOError, PermissionError):
            # If we can't read, assume binary to be safe
            return True

        return False
