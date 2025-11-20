"""Unit tests for VersionGraphBuilder service."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.deployment import Deployment
from skillmeat.core.version_graph import (
    ArtifactVersion,
    VersionGraph,
    VersionGraphBuilder,
    VersionGraphNode,
)


class TestArtifactVersion:
    """Tests for ArtifactVersion data model."""

    def test_artifact_version_creation(self):
        """Test creating an ArtifactVersion."""
        version = ArtifactVersion(
            artifact_name="test-skill",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
            collection_name="default",
        )

        assert version.artifact_name == "test-skill"
        assert version.artifact_type == "skill"
        assert version.content_sha == "abc123"
        assert version.location == "collection"
        assert version.location_type == "collection"
        assert version.collection_name == "default"
        assert version.parent_sha is None

    def test_is_modified_no_parent(self):
        """Test is_modified returns False when no parent."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )

        assert not version.is_modified()

    def test_is_modified_same_as_parent(self):
        """Test is_modified returns False when SHA matches parent."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="project",
            location_type="project",
            parent_sha="abc123",
        )

        assert not version.is_modified()

    def test_is_modified_different_from_parent(self):
        """Test is_modified returns True when SHA differs from parent."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="def456",
            location="project",
            location_type="project",
            parent_sha="abc123",
        )

        assert version.is_modified()


class TestVersionGraphNode:
    """Tests for VersionGraphNode data model."""

    def test_node_creation(self):
        """Test creating a VersionGraphNode."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )

        node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=version,
        )

        assert node.artifact_name == "test"
        assert node.artifact_type == "skill"
        assert node.version == version
        assert len(node.children) == 0
        assert len(node.metadata) == 0

    def test_is_collection_root_true(self):
        """Test is_collection_root property for collection node."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )

        node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=version,
        )

        assert node.is_collection_root

    def test_is_collection_root_false(self):
        """Test is_collection_root property for project node."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="/path/to/project",
            location_type="project",
        )

        node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=version,
        )

        assert not node.is_collection_root

    def test_modification_count_no_children(self):
        """Test modification_count with no children."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )

        node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=version,
        )

        assert node.modification_count == 0

    def test_modification_count_with_modified_children(self):
        """Test modification_count with modified children."""
        # Root node
        root_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=root_version,
        )

        # Modified child 1
        child1_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="def456",
            location="/project1",
            location_type="project",
            parent_sha="abc123",
        )
        child1 = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child1_version,
        )

        # Unmodified child 2
        child2_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="/project2",
            location_type="project",
            parent_sha="abc123",
        )
        child2 = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child2_version,
        )

        root.children = [child1, child2]

        assert root.modification_count == 1  # Only child1 is modified

    def test_total_instances(self):
        """Test total_instances counts self and all descendants."""
        # Root
        root_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=root_version,
        )

        # Child 1
        child1_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="def456",
            location="/project1",
            location_type="project",
            parent_sha="abc123",
        )
        child1 = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child1_version,
        )

        # Child 2
        child2_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="ghi789",
            location="/project2",
            location_type="project",
            parent_sha="abc123",
        )
        child2 = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child2_version,
        )

        root.children = [child1, child2]

        assert root.total_instances == 3  # root + child1 + child2


class TestVersionGraph:
    """Tests for VersionGraph data model."""

    def test_graph_creation_with_root(self):
        """Test creating a VersionGraph with root node."""
        version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=version,
        )

        graph = VersionGraph(
            artifact_name="test",
            artifact_type="skill",
            root=root,
            total_deployments=0,
            modified_count=0,
        )

        assert graph.artifact_name == "test"
        assert graph.artifact_type == "skill"
        assert graph.root == root
        assert len(graph.orphaned_nodes) == 0

    def test_graph_creation_without_root(self):
        """Test creating a VersionGraph without root (orphans only)."""
        graph = VersionGraph(
            artifact_name="test",
            artifact_type="skill",
            root=None,
            total_deployments=0,
            modified_count=0,
        )

        assert graph.root is None
        assert len(graph.orphaned_nodes) == 0

    def test_get_all_nodes_with_tree(self):
        """Test get_all_nodes returns all nodes in tree."""
        # Root
        root_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=root_version,
        )

        # Child
        child_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="def456",
            location="/project1",
            location_type="project",
            parent_sha="abc123",
        )
        child = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child_version,
        )
        root.children = [child]

        # Orphan
        orphan_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="ghi789",
            location="/project2",
            location_type="project",
            parent_sha="xyz999",  # Different parent
        )
        orphan = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=orphan_version,
        )

        graph = VersionGraph(
            artifact_name="test",
            artifact_type="skill",
            root=root,
            orphaned_nodes=[orphan],
            total_deployments=2,
            modified_count=1,
        )

        all_nodes = graph.get_all_nodes()
        assert len(all_nodes) == 3  # root + child + orphan
        assert root in all_nodes
        assert child in all_nodes
        assert orphan in all_nodes


class TestVersionGraphBuilder:
    """Tests for VersionGraphBuilder service."""

    @pytest.fixture
    def mock_collection_mgr(self):
        """Create a mock CollectionManager."""
        return MagicMock()

    @pytest.fixture
    def builder(self, mock_collection_mgr):
        """Create a VersionGraphBuilder with mocked dependencies."""
        return VersionGraphBuilder(collection_mgr=mock_collection_mgr)

    def test_builder_initialization(self):
        """Test VersionGraphBuilder initialization."""
        builder = VersionGraphBuilder()
        assert builder.collection_mgr is not None
        assert len(builder._cache) == 0

    def test_build_graph_invalid_artifact_id(self, builder):
        """Test build_graph with invalid artifact_id format."""
        with pytest.raises(ValueError, match="Invalid artifact_id format"):
            builder.build_graph("invalid_id")

    def test_build_graph_invalid_artifact_type(self, builder):
        """Test build_graph with invalid artifact type."""
        with pytest.raises(ValueError, match="Invalid artifact type"):
            builder.build_graph("invalid_type:test")

    @patch.object(VersionGraphBuilder, "_find_collection_version")
    @patch.object(VersionGraphBuilder, "_find_all_deployments")
    def test_build_graph_no_collection_no_deployments(
        self, mock_find_deployments, mock_find_collection, builder
    ):
        """Test build_graph when artifact doesn't exist anywhere."""
        mock_find_collection.return_value = None
        mock_find_deployments.return_value = []

        graph = builder.build_graph("skill:nonexistent")

        assert graph.artifact_name == "nonexistent"
        assert graph.artifact_type == "skill"
        assert graph.root is None
        assert len(graph.orphaned_nodes) == 0
        assert graph.total_deployments == 0
        assert graph.modified_count == 0

    @patch.object(VersionGraphBuilder, "_find_collection_version")
    @patch.object(VersionGraphBuilder, "_find_all_deployments")
    @patch.object(VersionGraphBuilder, "_build_project_node")
    def test_build_graph_with_collection_and_deployments(
        self,
        mock_build_node,
        mock_find_deployments,
        mock_find_collection,
        builder,
    ):
        """Test build_graph with collection root and matching deployments."""
        # Mock collection root
        root_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root_node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=root_version,
        )
        mock_find_collection.return_value = root_node

        # Mock deployment
        deployment = Mock(spec=Deployment)
        deployment.artifact_name = "test"
        deployment.artifact_type = "skill"
        deployment.collection_sha = "abc123"
        mock_find_deployments.return_value = [deployment]

        # Mock child node (matching parent SHA)
        child_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",  # Same as parent (unmodified)
            location="/project1",
            location_type="project",
            parent_sha="abc123",
        )
        child_node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=child_version,
        )
        mock_build_node.return_value = child_node

        graph = builder.build_graph("skill:test")

        assert graph.root == root_node
        assert len(root_node.children) == 1
        assert root_node.children[0] == child_node
        assert len(graph.orphaned_nodes) == 0
        assert graph.total_deployments == 1

    @patch.object(VersionGraphBuilder, "_find_collection_version")
    @patch.object(VersionGraphBuilder, "_find_all_deployments")
    @patch.object(VersionGraphBuilder, "_build_project_node")
    def test_build_graph_with_orphaned_deployment(
        self,
        mock_build_node,
        mock_find_deployments,
        mock_find_collection,
        builder,
    ):
        """Test build_graph with deployment that doesn't match collection SHA."""
        # Mock collection root
        root_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="abc123",
            location="collection",
            location_type="collection",
        )
        root_node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=root_version,
        )
        mock_find_collection.return_value = root_node

        # Mock deployment with different parent SHA
        deployment = Mock(spec=Deployment)
        deployment.artifact_name = "test"
        deployment.artifact_type = "skill"
        deployment.collection_sha = "old123"  # Different from collection
        mock_find_deployments.return_value = [deployment]

        # Mock orphaned node (different parent SHA)
        orphan_version = ArtifactVersion(
            artifact_name="test",
            artifact_type="skill",
            content_sha="def456",
            location="/project1",
            location_type="project",
            parent_sha="old123",  # Doesn't match root
        )
        orphan_node = VersionGraphNode(
            artifact_name="test",
            artifact_type="skill",
            version=orphan_version,
        )
        mock_build_node.return_value = orphan_node

        graph = builder.build_graph("skill:test")

        assert graph.root == root_node
        assert len(root_node.children) == 0  # No children attached to root
        assert len(graph.orphaned_nodes) == 1  # Orphaned deployment
        assert graph.orphaned_nodes[0] == orphan_node

    def test_cache_behavior(self, builder):
        """Test that cache stores and retrieves graphs."""
        # Mock the build process
        with patch.object(builder, "_find_collection_version", return_value=None), patch.object(
            builder, "_find_all_deployments", return_value=[]
        ):
            # First call - should build
            graph1 = builder.build_graph("skill:test")
            assert len(builder._cache) == 1

            # Second call - should use cache
            graph2 = builder.build_graph("skill:test")
            assert graph1 is graph2  # Same instance from cache

    def test_clear_cache(self, builder):
        """Test clearing the cache."""
        # Add something to cache
        with patch.object(builder, "_find_collection_version", return_value=None), patch.object(
            builder, "_find_all_deployments", return_value=[]
        ):
            builder.build_graph("skill:test")
            assert len(builder._cache) == 1

        # Clear cache
        builder.clear_cache()
        assert len(builder._cache) == 0

    def test_get_cache_stats(self, builder):
        """Test getting cache statistics."""
        stats = builder.get_cache_stats()

        assert "total_entries" in stats
        assert "valid_entries" in stats
        assert "expired_entries" in stats
        assert "cache_ttl_seconds" in stats
        assert stats["cache_ttl_seconds"] == 300  # 5 minutes

    def test_discover_projects_empty(self, builder):
        """Test project discovery when no projects found."""
        with patch("pathlib.Path.home") as mock_home, patch(
            "pathlib.Path.cwd"
        ) as mock_cwd:
            # Mock home to non-existent location
            mock_home.return_value = Path("/nonexistent")
            mock_cwd.return_value = Path("/nonexistent/cwd")

            projects = builder._discover_projects()
            assert isinstance(projects, list)
            # May be empty or contain only valid paths

    def test_find_collection_version_not_found(self, builder, mock_collection_mgr):
        """Test _find_collection_version when artifact not in collection."""
        mock_collection = Mock(spec=Collection)
        mock_collection.find_artifact.return_value = None
        mock_collection_mgr.load_collection.return_value = mock_collection

        result = builder._find_collection_version("test", ArtifactType.SKILL, None)

        assert result is None

    def test_find_collection_version_found(self, builder, mock_collection_mgr):
        """Test _find_collection_version when artifact exists."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = Path(tmpdir) / "collection"
            collection_path.mkdir()

            # Create a dummy skill directory
            skill_path = collection_path / "skills" / "test-skill"
            skill_path.mkdir(parents=True)
            (skill_path / "SKILL.md").write_text("# Test Skill")

            # Mock collection
            mock_artifact = Mock(spec=Artifact)
            mock_artifact.name = "test-skill"
            mock_artifact.type = ArtifactType.SKILL
            mock_artifact.path = "skills/test-skill"
            mock_artifact.added = datetime.now()
            mock_artifact.origin = "local"
            mock_artifact.upstream = None
            mock_artifact.version_spec = None
            mock_artifact.resolved_sha = None
            mock_artifact.resolved_version = None

            mock_collection = Mock(spec=Collection)
            mock_collection.name = "default"
            mock_collection.find_artifact.return_value = mock_artifact

            mock_collection_mgr.load_collection.return_value = mock_collection
            mock_collection_mgr.config.get_collection_path.return_value = collection_path

            result = builder._find_collection_version("test-skill", ArtifactType.SKILL, None)

            assert result is not None
            assert result.artifact_name == "test-skill"
            assert result.artifact_type == "skill"
            assert result.is_collection_root
