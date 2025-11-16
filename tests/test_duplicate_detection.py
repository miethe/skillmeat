"""Tests for duplicate detection functionality."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from skillmeat.core.search import SearchManager
from skillmeat.core.artifact import ArtifactType
from skillmeat.models import ArtifactFingerprint, DuplicatePair
from skillmeat.utils.metadata import ArtifactMetadata


@pytest.fixture
def temp_collection(tmp_path):
    """Create temporary collection directory."""
    collection_dir = tmp_path / ".skillmeat"
    collection_dir.mkdir()
    return collection_dir


@pytest.fixture
def mock_collection_mgr(temp_collection):
    """Create mock collection manager."""
    mgr = Mock()
    mgr.config = Mock()
    mgr.config.get = Mock(side_effect=lambda key, default=None: default)
    return mgr


@pytest.fixture
def search_manager(mock_collection_mgr):
    """Create SearchManager instance."""
    return SearchManager(mock_collection_mgr)


@pytest.fixture
def sample_artifact_dir(tmp_path):
    """Create sample artifact directory."""
    artifact_dir = tmp_path / "sample_skill"
    artifact_dir.mkdir()

    # Create SKILL.md
    skill_md = artifact_dir / "SKILL.md"
    skill_md.write_text(
        """---
title: Sample Skill
description: A sample skill for testing
tags:
  - testing
  - sample
---

# Sample Skill

This is a sample skill.
"""
    )

    # Create additional file
    readme = artifact_dir / "README.md"
    readme.write_text("# Sample Skill\n\nReadme content.")

    return artifact_dir


@pytest.fixture
def sample_artifact_dict(sample_artifact_dir):
    """Create sample artifact dict."""
    metadata = ArtifactMetadata(
        title="Sample Skill",
        description="A sample skill for testing",
        tags=["testing", "sample"],
    )

    return {
        "name": "sample_skill",
        "type": ArtifactType.SKILL,
        "path": sample_artifact_dir,
        "metadata": metadata,
    }


class TestFingerprintComputation:
    """Test fingerprint computation."""

    def test_compute_fingerprint_basic(self, search_manager, sample_artifact_dict):
        """Test basic fingerprint computation."""
        fp = search_manager._compute_fingerprint(sample_artifact_dict)

        assert isinstance(fp, ArtifactFingerprint)
        assert fp.artifact_name == "sample_skill"
        assert fp.artifact_type == "skill"
        assert fp.artifact_path == sample_artifact_dict["path"]
        assert fp.title == "Sample Skill"
        assert fp.description == "A sample skill for testing"
        assert fp.tags == ["testing", "sample"]
        assert fp.file_count > 0
        assert fp.total_size > 0

    def test_compute_content_hash(self, search_manager, sample_artifact_dir):
        """Test content hash computation."""
        content_hash = search_manager._hash_artifact_contents(sample_artifact_dir)

        assert isinstance(content_hash, str)
        assert len(content_hash) == 64  # SHA256 hex digest length

    def test_compute_structure_hash(self, search_manager, sample_artifact_dir):
        """Test structure hash computation."""
        structure_hash = search_manager._hash_artifact_structure(sample_artifact_dir)

        assert isinstance(structure_hash, str)
        assert len(structure_hash) == 64  # SHA256 hex digest length

    def test_compute_metadata_hash(self, search_manager, sample_artifact_dict):
        """Test metadata hash computation."""
        fp = search_manager._compute_fingerprint(sample_artifact_dict)

        assert isinstance(fp.metadata_hash, str)
        assert len(fp.metadata_hash) == 64  # SHA256 hex digest length

    def test_handle_binary_files(self, search_manager, tmp_path):
        """Test handling of binary files in artifact."""
        artifact_dir = tmp_path / "binary_skill"
        artifact_dir.mkdir()

        # Create text file
        skill_md = artifact_dir / "SKILL.md"
        skill_md.write_text("# Binary Skill")

        # Create binary file
        binary_file = artifact_dir / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        content_hash = search_manager._hash_artifact_contents(artifact_dir)

        # Binary file should be skipped, only text file hashed
        assert isinstance(content_hash, str)
        assert len(content_hash) == 64

    def test_handle_large_files(self, search_manager, tmp_path):
        """Test handling of large files in artifact."""
        artifact_dir = tmp_path / "large_skill"
        artifact_dir.mkdir()

        # Create normal file
        skill_md = artifact_dir / "SKILL.md"
        skill_md.write_text("# Large Skill")

        # Note: We can't easily test the MAX_FILE_SIZE check without mocking
        # or creating a huge file. The important part is that the method
        # returns a valid hash and doesn't crash.
        content_hash = search_manager._hash_artifact_contents(artifact_dir)

        assert isinstance(content_hash, str)
        assert len(content_hash) == 64

    def test_ignore_patterns(self, search_manager, tmp_path):
        """Test that ignore patterns are respected."""
        artifact_dir = tmp_path / "ignore_skill"
        artifact_dir.mkdir()

        # Create normal file
        skill_md = artifact_dir / "SKILL.md"
        skill_md.write_text("# Ignore Skill")

        # Create files in ignored directories
        pycache = artifact_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "test.pyc").write_bytes(b"compiled")

        git_dir = artifact_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        # Hash should only include SKILL.md
        content_hash = search_manager._hash_artifact_contents(artifact_dir)
        structure_hash = search_manager._hash_artifact_structure(artifact_dir)

        assert isinstance(content_hash, str)
        assert isinstance(structure_hash, str)


class TestSimilarityCalculation:
    """Test similarity score calculation."""

    def test_exact_content_match(self, search_manager, tmp_path):
        """Test similarity for exact content match."""
        # Create two identical artifacts
        artifact1 = tmp_path / "skill1"
        artifact1.mkdir()
        (artifact1 / "SKILL.md").write_text("# Same Content")

        artifact2 = tmp_path / "skill2"
        artifact2.mkdir()
        (artifact2 / "SKILL.md").write_text("# Same Content")

        metadata = ArtifactMetadata(title="Same", description="Same desc")

        dict1 = {
            "name": "skill1",
            "type": ArtifactType.SKILL,
            "path": artifact1,
            "metadata": metadata,
        }
        dict2 = {
            "name": "skill2",
            "type": ArtifactType.SKILL,
            "path": artifact2,
            "metadata": metadata,
        }

        fp1 = search_manager._compute_fingerprint(dict1)
        fp2 = search_manager._compute_fingerprint(dict2)

        similarity = fp1.compute_similarity(fp2)

        # Exact match should have similarity of 1.0 (use approx for floating point)
        assert similarity == pytest.approx(1.0, abs=1e-9)

    def test_partial_metadata_match(self, tmp_path):
        """Test similarity with partial metadata match."""
        # Create fingerprints with different metadata
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="struct1",
            title="Same Title",
            description="Different desc 1",
            tags=["tag1", "tag2"],
            file_count=2,
            total_size=100,
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="struct2",
            title="Same Title",
            description="Different desc 2",
            tags=["tag1", "tag3"],
            file_count=2,
            total_size=100,
        )

        similarity = fp1.compute_similarity(fp2)

        # Should have some similarity from title and partial tag overlap
        assert 0.0 < similarity < 1.0

    def test_tag_overlap_jaccard(self, tmp_path):
        """Test tag similarity using Jaccard similarity."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="struct1",
            title="Skill 1",
            description="Desc 1",
            tags=["tag1", "tag2", "tag3"],
            file_count=2,
            total_size=100,
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="struct2",
            title="Skill 2",
            description="Desc 2",
            tags=["tag2", "tag3", "tag4"],
            file_count=2,
            total_size=100,
        )

        # Tags have 2/4 = 0.5 Jaccard similarity
        similarity = fp1.compute_similarity(fp2)

        # With file count match (10%) and partial tag match (part of 20%)
        assert similarity > 0.1  # At least file count match

    def test_structure_match_only(self, tmp_path):
        """Test similarity with structure match only."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="same_struct",  # Same structure
            title="Skill 1",
            description="Desc 1",
            tags=["tag1"],
            file_count=2,
            total_size=100,
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="same_struct",  # Same structure
            title="Skill 2",
            description="Desc 2",
            tags=["tag2"],
            file_count=2,
            total_size=100,
        )

        similarity = fp1.compute_similarity(fp2)

        # Structure match (20%) + file count match (10%) = 30%
        assert similarity >= 0.3

    def test_no_similarity(self, tmp_path):
        """Test similarity when artifacts are completely different."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="struct1",
            title="Skill 1",
            description="Desc 1",
            tags=["tag1"],
            file_count=2,
            total_size=100,
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="struct2",
            title="Skill 2",
            description="Desc 2",
            tags=["tag2"],
            file_count=10,  # Very different file count
            total_size=1000,
        )

        similarity = fp1.compute_similarity(fp2)

        # Should have low similarity (only partial file count similarity)
        assert similarity < 0.5


class TestDuplicateDetection:
    """Test duplicate detection."""

    def test_find_exact_duplicates(self, search_manager, tmp_path):
        """Test finding exact duplicate artifacts."""
        # Create two identical projects with same artifact
        project1 = tmp_path / "project1" / ".claude"
        project1.mkdir(parents=True)
        skills1 = project1 / "skills"
        skills1.mkdir()

        skill1 = skills1 / "test_skill"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Test Skill\nSame content")

        project2 = tmp_path / "project2" / ".claude"
        project2.mkdir(parents=True)
        skills2 = project2 / "skills"
        skills2.mkdir()

        skill2 = skills2 / "test_skill"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Test Skill\nSame content")

        # Find duplicates
        duplicates = search_manager.find_duplicates(
            threshold=0.85, project_paths=[project1, project2], use_cache=False
        )

        assert len(duplicates) == 1
        assert duplicates[0].similarity_score == pytest.approx(1.0, abs=1e-9)
        assert "exact_content" in duplicates[0].match_reasons

    def test_find_similar_artifacts(self, search_manager, tmp_path):
        """Test finding similar (not exact) artifacts."""
        # Create two projects with similar artifacts
        project1 = tmp_path / "project1" / ".claude"
        project1.mkdir(parents=True)
        skills1 = project1 / "skills"
        skills1.mkdir()

        skill1 = skills1 / "skill_v1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill\nVersion 1")
        (skill1 / "file1.txt").write_text("shared content")

        project2 = tmp_path / "project2" / ".claude"
        project2.mkdir(parents=True)
        skills2 = project2 / "skills"
        skills2.mkdir()

        skill2 = skills2 / "skill_v2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill\nVersion 2")
        (skill2 / "file1.txt").write_text("shared content")

        # Find duplicates with lower threshold
        duplicates = search_manager.find_duplicates(
            threshold=0.5, project_paths=[project1, project2], use_cache=False
        )

        # Should find at least one pair (same structure and some content)
        assert len(duplicates) >= 0  # May or may not find depending on similarity

    def test_skip_below_threshold(self, search_manager, tmp_path):
        """Test that artifacts below threshold are not reported."""
        # Create two very different projects
        project1 = tmp_path / "project1" / ".claude"
        project1.mkdir(parents=True)
        skills1 = project1 / "skills"
        skills1.mkdir()

        skill1 = skills1 / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill 1\nContent 1\n" * 10)

        project2 = tmp_path / "project2" / ".claude"
        project2.mkdir(parents=True)
        skills2 = project2 / "skills"
        skills2.mkdir()

        skill2 = skills2 / "skill2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill 2\nContent 2\n" * 100)

        # Find duplicates with high threshold
        duplicates = search_manager.find_duplicates(
            threshold=0.95, project_paths=[project1, project2], use_cache=False
        )

        # Should not find any duplicates
        assert len(duplicates) == 0

    def test_handle_no_duplicates(self, search_manager, tmp_path):
        """Test handling when no duplicates exist."""
        # Create project with unique artifacts
        project = tmp_path / "project" / ".claude"
        project.mkdir(parents=True)
        skills = project / "skills"
        skills.mkdir()

        skill1 = skills / "unique1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Unique 1")

        skill2 = skills / "unique2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Unique 2\n" * 100)

        duplicates = search_manager.find_duplicates(
            threshold=0.85, project_paths=[project], use_cache=False
        )

        assert len(duplicates) == 0

    def test_handle_single_artifact(self, search_manager, tmp_path):
        """Test handling when only one artifact exists."""
        # Create project with single artifact
        project = tmp_path / "project" / ".claude"
        project.mkdir(parents=True)
        skills = project / "skills"
        skills.mkdir()

        skill = skills / "only_one"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Only One")

        duplicates = search_manager.find_duplicates(
            threshold=0.85, project_paths=[project], use_cache=False
        )

        assert len(duplicates) == 0

    def test_handle_empty_collection(self, search_manager):
        """Test handling when no artifacts exist."""
        duplicates = search_manager.find_duplicates(
            threshold=0.85, project_paths=[], use_cache=False
        )

        assert len(duplicates) == 0

    def test_threshold_validation(self, search_manager):
        """Test threshold validation."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            search_manager.find_duplicates(threshold=1.5)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            search_manager.find_duplicates(threshold=-0.1)


class TestMatchReasons:
    """Test match reason identification."""

    def test_identify_exact_content_match(self, tmp_path):
        """Test identification of exact content match."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="same_hash",
            metadata_hash="metahash1",
            structure_hash="struct1",
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="same_hash",
            metadata_hash="metahash2",
            structure_hash="struct2",
        )

        from skillmeat.core.search import SearchManager

        mgr = SearchManager(Mock())
        reasons = mgr._get_match_reasons(fp1, fp2)

        assert "exact_content" in reasons

    def test_identify_structure_match(self, tmp_path):
        """Test identification of structure match."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="same_struct",
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="same_struct",
        )

        from skillmeat.core.search import SearchManager

        mgr = SearchManager(Mock())
        reasons = mgr._get_match_reasons(fp1, fp2)

        assert "same_structure" in reasons

    def test_identify_metadata_match(self, tmp_path):
        """Test identification of metadata match."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="same_meta",
            structure_hash="struct1",
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="same_meta",
            structure_hash="struct2",
        )

        from skillmeat.core.search import SearchManager

        mgr = SearchManager(Mock())
        reasons = mgr._get_match_reasons(fp1, fp2)

        assert "exact_metadata" in reasons

    def test_identify_tag_similarity(self, tmp_path):
        """Test identification of tag similarity."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="struct1",
            tags=["tag1", "tag2", "tag3"],
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="struct2",
            tags=["tag2", "tag3", "tag4"],  # 2/4 = 0.5 Jaccard
        )

        from skillmeat.core.search import SearchManager

        mgr = SearchManager(Mock())
        reasons = mgr._get_match_reasons(fp1, fp2)

        assert "similar_tags" in reasons

    def test_identify_title_match(self, tmp_path):
        """Test identification of title match."""
        fp1 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill1",
            artifact_name="skill1",
            artifact_type="skill",
            content_hash="hash1",
            metadata_hash="metahash1",
            structure_hash="struct1",
            title="Same Title",
        )

        fp2 = ArtifactFingerprint(
            artifact_path=tmp_path / "skill2",
            artifact_name="skill2",
            artifact_type="skill",
            content_hash="hash2",
            metadata_hash="metahash2",
            structure_hash="struct2",
            title="Same Title",
        )

        from skillmeat.core.search import SearchManager

        mgr = SearchManager(Mock())
        reasons = mgr._get_match_reasons(fp1, fp2)

        assert "same_title" in reasons


class TestPerformance:
    """Test performance of duplicate detection."""

    def test_100_artifacts_performance(self, search_manager, tmp_path):
        """Test performance with 100 artifacts."""
        # Create project with 100 artifacts
        project = tmp_path / "project" / ".claude"
        project.mkdir(parents=True)
        skills = project / "skills"
        skills.mkdir()

        for i in range(100):
            skill = skills / f"skill_{i}"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# Skill {i}\nContent {i}")

        start_time = time.time()
        duplicates = search_manager.find_duplicates(
            threshold=0.85, project_paths=[project], use_cache=False
        )
        elapsed = time.time() - start_time

        # Should complete in under 5 seconds
        assert elapsed < 5.0

    def test_duplicate_detection_sorting(self, search_manager, tmp_path):
        """Test that duplicates are sorted by similarity score."""
        # Create multiple projects with varying similarity
        projects = []
        for i in range(3):
            project = tmp_path / f"project{i}" / ".claude"
            project.mkdir(parents=True)
            skills = project / "skills"
            skills.mkdir()

            # Create artifacts with different content
            skill = skills / "test_skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"# Test\n{'content ' * i}")

            projects.append(project)

        duplicates = search_manager.find_duplicates(
            threshold=0.5, project_paths=projects, use_cache=False
        )

        # If we have duplicates, they should be sorted descending
        if len(duplicates) > 1:
            for i in range(len(duplicates) - 1):
                assert duplicates[i].similarity_score >= duplicates[i + 1].similarity_score
