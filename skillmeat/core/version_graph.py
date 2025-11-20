"""Version graph building and management for artifact deployments across collections and projects.

This module implements the version tracking system described in ADR-004, enabling
visualization of artifact deployment relationships and modification tracking.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.deployment import Deployment
from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.utils.filesystem import compute_content_hash
from skillmeat.utils.logging import redact_path


@dataclass
class ArtifactVersion:
    """Represents a specific version of an artifact at a point in time.

    This tracks both collection artifacts (canonical versions) and project
    deployments (instances with potential local modifications).

    Attributes:
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        content_sha: SHA-256 hash of all artifact content
        location: Either "collection" or absolute project path
        location_type: Whether this is a collection or project version
        collection_name: Name of source collection (if applicable)
        parent_sha: SHA-256 hash of parent version (if deployed from collection)
        created_at: Timestamp when this version was created
        metadata_snapshot: Optional metadata captured at this point in time
    """

    artifact_name: str
    artifact_type: str  # ArtifactType.value
    content_sha: str  # SHA-256 hash of all content
    location: str  # "collection" or absolute project path
    location_type: Literal["collection", "project"]  # Type-safe literal
    collection_name: Optional[str] = None  # Source collection
    parent_sha: Optional[str] = None  # SHA of parent version (if deployed from collection)
    created_at: datetime = field(default_factory=datetime.now)
    metadata_snapshot: Optional[Dict[str, Any]] = None

    def is_modified(self) -> bool:
        """Check if this version differs from its parent.

        Returns:
            True if content differs from parent, False otherwise
        """
        return self.parent_sha is not None and self.parent_sha != self.content_sha


@dataclass
class VersionGraphNode:
    """Node in the artifact version graph.

    Represents a single version (either collection root or project deployment)
    with its children (deployments derived from this version). Forms a tree
    structure with the collection version as root and project versions as children.

    Attributes:
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        version: The ArtifactVersion this node represents
        children: List of child nodes (deployed/derived versions)
        metadata: Additional node-specific metadata
    """

    artifact_name: str
    artifact_type: str
    version: ArtifactVersion
    children: List["VersionGraphNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_collection_root(self) -> bool:
        """True if this is the canonical collection version.

        Returns:
            True for collection root nodes, False for project deployments
        """
        return self.version.location_type == "collection"

    @property
    def is_modified(self) -> bool:
        """True if content differs from parent.

        Returns:
            True if this node represents a modified version
        """
        return self.version.is_modified()

    @property
    def modification_count(self) -> int:
        """Count of modified children (recursive).

        Recursively counts all modified descendant nodes in the tree.

        Returns:
            Total number of modified nodes in subtree
        """
        count = 0
        for child in self.children:
            if child.is_modified:
                count += 1
            count += child.modification_count
        return count

    @property
    def total_instances(self) -> int:
        """Count total instances including this node (recursive).

        Returns:
            Total number of nodes in subtree including self
        """
        count = 1  # Count self
        for child in self.children:
            count += child.total_instances
        return count


@dataclass
class VersionGraph:
    """Complete version graph for an artifact across all projects.

    Represents the entire deployment tree for a single artifact, showing the
    canonical collection version and all deployed/modified project versions.
    Supports both rooted graphs (with collection version) and orphaned nodes
    (project versions without a collection parent).

    Attributes:
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        root: Root node (collection version), if exists
        orphaned_nodes: Project versions without a collection parent
        total_deployments: Total count of deployments across all projects
        modified_count: Count of deployments with local modifications
        last_updated: Timestamp when this graph was last computed
    """

    artifact_name: str
    artifact_type: str
    root: Optional[VersionGraphNode] = None  # Collection version (canonical)
    orphaned_nodes: List[VersionGraphNode] = field(default_factory=list)  # No parent in collection
    total_deployments: int = 0
    modified_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def get_all_nodes(self) -> List[VersionGraphNode]:
        """Flatten graph to list of all nodes.

        Returns a flat list containing all nodes in the version graph,
        including both the rooted tree and any orphaned nodes.

        Returns:
            List containing all nodes (root tree + orphans)
        """
        nodes = []
        if self.root:
            nodes.extend(self._traverse(self.root))
        nodes.extend(self.orphaned_nodes)
        return nodes

    def _traverse(self, node: VersionGraphNode) -> List[VersionGraphNode]:
        """Recursively traverse graph.

        Performs a depth-first traversal of the version tree starting
        from the given node.

        Args:
            node: Node to start traversal from

        Returns:
            List of all nodes in subtree
        """
        result = [node]
        for child in node.children:
            result.extend(self._traverse(child))
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Compute graph statistics.

        Returns:
            Dictionary with statistics including total_deployments,
            modified_count, unmodified_count, and orphaned_count
        """
        all_nodes = self.get_all_nodes()
        # Exclude root node from deployment counts
        deployment_nodes = [n for n in all_nodes if not n.is_collection_root]

        modified = sum(1 for n in deployment_nodes if n.is_modified)
        unmodified = len(deployment_nodes) - modified

        return {
            "total_deployments": len(deployment_nodes),
            "modified_count": modified,
            "unmodified_count": unmodified,
            "orphaned_count": len(self.orphaned_nodes),
        }


class VersionGraphBuilder:
    """Builds version graphs for artifacts across collections and projects.

    This service constructs the complete version tree for an artifact, showing:
    - Canonical collection version (root)
    - All project deployments (children)
    - Modification status for each deployment
    - Orphaned deployments (no matching collection version)

    Implements caching with 5-minute TTL for performance.
    """

    # Cache duration in seconds
    CACHE_TTL = 300  # 5 minutes

    def __init__(self, collection_mgr: Optional[CollectionManager] = None):
        """Initialize version graph builder.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
        """
        if collection_mgr is None:
            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr
        self._cache: Dict[str, tuple[VersionGraph, datetime]] = {}
        self.logger = logging.getLogger(__name__)

    def build_graph(
        self,
        artifact_id: str,
        collection_name: Optional[str] = None,
    ) -> VersionGraph:
        """Build complete version graph for an artifact.

        Algorithm (from ADR-004):
        1. Load collection artifact (root)
        2. Find all project deployments
        3. Build parent-child relationships using content_hash
        4. Attach orphaned nodes separately
        5. Calculate recursive statistics

        Args:
            artifact_id: Artifact identifier in format "type:name" (e.g., "skill:pdf-processor")
            collection_name: Optional collection to filter by (uses active if None)

        Returns:
            VersionGraph with complete deployment tree

        Raises:
            ValueError: If artifact_id format is invalid
        """
        # Check cache first
        cache_key = f"{artifact_id}:{collection_name or 'default'}"
        if cache_key in self._cache:
            cached_graph, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.CACHE_TTL):
                self.logger.debug(f"Returning cached graph for {artifact_id}")
                return cached_graph

        # Parse artifact_id
        parts = artifact_id.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid artifact_id format '{artifact_id}'. "
                "Expected 'type:name' (e.g., 'skill:pdf-processor')"
            )

        artifact_type_str, artifact_name = parts

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            raise ValueError(
                f"Invalid artifact type '{artifact_type_str}'. "
                f"Must be one of: {', '.join([t.value for t in ArtifactType])}"
            )

        # 1. Find canonical version in collection (root)
        root_node = self._find_collection_version(
            artifact_name, artifact_type, collection_name
        )

        # 2. Find all project deployments
        deployments = self._find_all_deployments(artifact_name, artifact_type)

        # 3. Build tree structure
        orphaned_nodes = []
        if root_node:
            # Build children for root node
            for deployment in deployments:
                child_node = self._build_project_node(deployment)

                # Check if this deployment's parent SHA matches root SHA
                if child_node.version.parent_sha == root_node.version.content_sha:
                    root_node.children.append(child_node)
                else:
                    # Orphaned: deployed from different version or modified parent
                    orphaned_nodes.append(child_node)
        else:
            # No collection version - all deployments are orphaned
            for deployment in deployments:
                child_node = self._build_project_node(deployment)
                orphaned_nodes.append(child_node)

        # 4. Calculate statistics
        total_deployments = len(deployments)
        modified_count = 0

        if root_node:
            modified_count = root_node.modification_count

        # Add orphaned modified nodes
        for orphan in orphaned_nodes:
            if orphan.is_modified:
                modified_count += 1
            modified_count += orphan.modification_count

        # 5. Create graph
        graph = VersionGraph(
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            root=root_node,
            orphaned_nodes=orphaned_nodes,
            total_deployments=total_deployments,
            modified_count=modified_count,
            last_updated=datetime.now(),
        )

        # Cache the result
        self._cache[cache_key] = (graph, datetime.now())

        self.logger.info(
            f"Built version graph for {artifact_id}: "
            f"{total_deployments} deployments, {modified_count} modified"
        )

        return graph

    def _find_collection_version(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str],
    ) -> Optional[VersionGraphNode]:
        """Find artifact in collection and create root node.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type
            collection_name: Collection name (uses active if None)

        Returns:
            VersionGraphNode for collection artifact, or None if not found
        """
        try:
            # Load collection
            collection = self.collection_mgr.load_collection(collection_name)
            collection_path = self.collection_mgr.config.get_collection_path(
                collection.name
            )

            # Find artifact in collection
            artifact = collection.find_artifact(artifact_name, artifact_type)
            if not artifact:
                self.logger.debug(
                    f"Artifact {artifact_type.value}/{artifact_name} "
                    f"not found in collection {collection.name}"
                )
                return None

            # Get artifact path and compute hash
            artifact_path = collection_path / artifact.path
            if not artifact_path.exists():
                self.logger.warning(
                    f"Artifact path missing: {redact_path(artifact_path)}"
                )
                return None

            content_sha = compute_content_hash(artifact_path)

            # Create version info
            version = ArtifactVersion(
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                content_sha=content_sha,
                location="collection",
                location_type="collection",
                collection_name=collection.name,
                parent_sha=None,  # Collection root has no parent
                created_at=artifact.added,
                metadata_snapshot={
                    "origin": artifact.origin,
                    "upstream": artifact.upstream,
                    "version_spec": artifact.version_spec,
                    "resolved_sha": artifact.resolved_sha,
                    "resolved_version": artifact.resolved_version,
                },
            )

            # Create node
            node = VersionGraphNode(
                artifact_name=artifact_name,
                artifact_type=artifact_type.value,
                version=version,
                metadata={
                    "collection_name": collection.name,
                    "collection_path": str(collection_path),
                    "is_collection_root": True,
                },
            )

            return node

        except Exception as e:
            self.logger.error(
                f"Error finding collection version for {artifact_type.value}/{artifact_name}: {e}"
            )
            return None

    def _find_all_deployments(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
    ) -> List[Deployment]:
        """Find all deployments of an artifact across all projects.

        Scans all discovered projects for deployment records matching the
        specified artifact.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type

        Returns:
            List of Deployment objects with project_path attached
        """
        deployments = []

        # Discover all projects with .claude directories
        project_paths = self._discover_projects()

        for project_path in project_paths:
            try:
                # Read deployments from project
                project_deployments = DeploymentTracker.read_deployments(project_path)

                # Filter for matching artifacts
                for deployment in project_deployments:
                    if (
                        deployment.artifact_name == artifact_name
                        and deployment.artifact_type == artifact_type.value
                    ):
                        # Attach project_path for later use
                        deployment.project_path = project_path  # type: ignore
                        deployments.append(deployment)

            except Exception as e:
                self.logger.warning(
                    f"Error reading deployments from {redact_path(project_path)}: {e}"
                )
                continue

        self.logger.debug(
            f"Found {len(deployments)} deployments of {artifact_type.value}/{artifact_name}"
        )

        return deployments

    def _build_project_node(self, deployment: Deployment) -> VersionGraphNode:
        """Build version graph node for a project deployment.

        Args:
            deployment: Deployment record with project_path attached

        Returns:
            VersionGraphNode representing the deployment
        """
        project_path = getattr(deployment, "project_path", None)
        if not project_path:
            raise ValueError("Deployment missing project_path attribute")

        # Get artifact path
        artifact_path = project_path / ".claude" / deployment.artifact_path

        # Compute current content hash
        try:
            current_sha = compute_content_hash(artifact_path)
        except Exception as e:
            self.logger.warning(
                f"Could not compute hash for {redact_path(artifact_path)}: {e}"
            )
            # Use deployment SHA as fallback
            current_sha = deployment.collection_sha

        # Determine if modified
        is_modified = current_sha != deployment.collection_sha

        # Create version info
        version = ArtifactVersion(
            artifact_name=deployment.artifact_name,
            artifact_type=deployment.artifact_type,
            content_sha=current_sha,
            location=str(project_path),
            location_type="project",
            collection_name=deployment.from_collection,
            parent_sha=deployment.collection_sha,  # SHA at deployment time
            created_at=deployment.deployed_at,
            metadata_snapshot={
                "local_modifications": is_modified,
                "deployed_at": deployment.deployed_at.isoformat(),
            },
        )

        # Create node
        node = VersionGraphNode(
            artifact_name=deployment.artifact_name,
            artifact_type=deployment.artifact_type,
            version=version,
            metadata={
                "project_path": str(project_path),
                "project_name": project_path.name,
                "deployed_at": deployment.deployed_at,
                "is_modified": is_modified,
                "deployed_sha": deployment.collection_sha,
                "current_sha": current_sha,
            },
        )

        return node

    def _discover_projects(self) -> List[Path]:
        """Discover all projects with .claude directories.

        This is a simple implementation that checks:
        1. Common project locations (~/projects, ~/dev, ~/work)
        2. Current working directory and siblings

        Future enhancement: Use configuration for project discovery paths.

        Returns:
            List of absolute paths to project directories
        """
        projects: Set[Path] = set()

        # Check common project locations
        home = Path.home()
        common_locations = [
            home / "projects",
            home / "dev",
            home / "work",
            home / "code",
            home / "workspace",
        ]

        for location in common_locations:
            if location.exists() and location.is_dir():
                # Scan for .claude directories (1 level deep)
                try:
                    for child in location.iterdir():
                        if child.is_dir():
                            claude_dir = child / ".claude"
                            if claude_dir.exists() and claude_dir.is_dir():
                                projects.add(child)
                except PermissionError:
                    # Skip directories we can't read
                    continue

        # Check current working directory
        cwd = Path.cwd()
        if (cwd / ".claude").exists():
            projects.add(cwd)

        # Check CWD parent's children (sibling projects)
        try:
            if cwd.parent.exists():
                for sibling in cwd.parent.iterdir():
                    if sibling.is_dir() and (sibling / ".claude").exists():
                        projects.add(sibling)
        except PermissionError:
            pass

        result = sorted(projects)  # Sort for consistency
        self.logger.debug(f"Discovered {len(result)} projects with .claude directories")

        return result

    def clear_cache(self) -> None:
        """Clear the version graph cache.

        Useful after deployments or artifact updates to force rebuild.
        """
        self._cache.clear()
        self.logger.debug("Version graph cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache size and entry details
        """
        now = datetime.now()
        valid_entries = 0
        expired_entries = 0

        for cache_key, (_, cached_time) in self._cache.items():
            if now - cached_time < timedelta(seconds=self.CACHE_TTL):
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self.CACHE_TTL,
        }
