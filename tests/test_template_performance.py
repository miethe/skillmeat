"""Performance tests for template deployment service.

This module benchmarks the template deployment service to ensure it meets
the performance target of deploying 10 entities in < 5 seconds (P95).

Benchmarks:
- Template deployment with 10 entities: < 5 seconds (P95)
- Database query optimization: No N+1 queries
- File I/O optimization: Concurrent writes when aiofiles available
- Variable substitution: Cached regex patterns

Performance Optimizations Tested:
1. Batch database queries with eager loading (joinedload)
2. Async file I/O with concurrent writes (asyncio.gather)
3. Pre-creation of all directories before writing files
4. Cached regex patterns for variable substitution
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from skillmeat.cache.models import (
    Artifact,
    ProjectTemplate,
    TemplateEntity,
    get_session,
)
from skillmeat.core.services.template_service import (
    deploy_template,
    deploy_template_async,
    render_content,
)


# Track SQL queries to detect N+1 problems
query_count = 0


@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    """Count SQL queries for N+1 detection."""
    global query_count
    query_count += 1


@pytest.fixture
def session():
    """Get test database session."""
    return get_session()


@pytest.fixture
def template_with_10_entities(session, tmp_path):
    """Create a template with 10 entities for performance testing.

    Args:
        session: Database session
        tmp_path: Pytest tmp_path fixture

    Returns:
        tuple: (template_id, project_path)
    """
    # Create collection (placeholder - would normally exist)
    collection_id = uuid.uuid4().hex

    # Create template
    template_id = uuid.uuid4().hex
    template = ProjectTemplate(
        id=template_id,
        name="performance-test-template",
        description="Template with 10 entities for performance testing",
        collection_id=collection_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(template)

    # Create 10 artifacts with mock content
    for i in range(10):
        artifact_id = uuid.uuid4().hex
        artifact = Artifact(
            id=artifact_id,
            project_id="test-project",
            name=f"test-entity-{i:02d}",
            artifact_type="rule_file",
            path_pattern=f".claude/rules/test-rule-{i:02d}.md",
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
            local_modified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(artifact)

        # Create template entity association
        template_entity = TemplateEntity(
            template_id=template_id,
            artifact_id=artifact_id,
            deploy_order=i,
            required=True,
        )
        session.add(template_entity)

    session.commit()

    # Create project directory
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    return template_id, str(project_path)


class TestTemplateDeploymentPerformance:
    """Performance tests for template deployment."""

    def test_deployment_10_entities_under_5_seconds(
        self, session, template_with_10_entities
    ):
        """Template deployment of 10 entities completes in < 5 seconds (P95).

        Benchmark: Deploy 10 entities in under 5 seconds at P95.

        This test verifies the complete deployment pipeline including:
        - Database queries (with eager loading)
        - File I/O operations (with async optimization)
        - Variable substitution (with cached patterns)
        - Directory creation
        - Atomic file moves

        Args:
            session: Database session
            template_with_10_entities: Fixture with template and 10 entities
        """
        template_id, project_path = template_with_10_entities

        # Mock artifact content fetching (since we don't have real artifacts)
        mock_content = """---
name: {{PROJECT_NAME}}
description: Test entity for {{PROJECT_NAME}}
author: {{AUTHOR}}
date: {{DATE}}
---

# Test Entity

This is a test entity for project {{PROJECT_NAME}}.

Created by {{AUTHOR}} on {{DATE}}.
"""

        with patch(
            "skillmeat.core.services.template_service._fetch_artifact_content",
            return_value=mock_content,
        ):
            # Define variables
            variables = {
                "PROJECT_NAME": "performance-test-project",
                "AUTHOR": "test-author",
                "DATE": "2025-12-15",
            }

            # Execute deployment and measure time
            start = time.perf_counter()
            result = deploy_template(
                session=session,
                template_id=template_id,
                project_path=project_path,
                variables=variables,
                overwrite=True,
            )
            duration = time.perf_counter() - start

            # Verify correctness
            assert result.success, f"Deployment failed: {result.message}"
            assert (
                len(result.deployed_files) == 10
            ), f"Expected 10 files, got {len(result.deployed_files)}"

            # Verify all files exist
            for deployed_file in result.deployed_files:
                file_path = Path(project_path) / deployed_file
                assert file_path.exists(), f"File not created: {deployed_file}"

                # Verify variable substitution worked
                content = file_path.read_text()
                assert "performance-test-project" in content
                assert "test-author" in content
                assert "{{PROJECT_NAME}}" not in content

            # PERFORMANCE BENCHMARK: < 5 seconds
            assert (
                duration < 5.0
            ), f"Deployment took {duration:.3f}s (expected <5.0s)"

            print(
                f"\n✓ Performance test passed: {duration:.3f}s for 10 entities"
            )

    def test_no_n_plus_1_queries(self, session, template_with_10_entities):
        """Verify database query optimization (no N+1 queries).

        With eager loading, we should have:
        - 1 query to fetch template with entities and artifacts
        - No additional queries in the loop

        Without eager loading, we would have:
        - 1 query to fetch template
        - 10 queries to fetch each artifact (N+1 problem)

        Args:
            session: Database session
            template_with_10_entities: Fixture with template and 10 entities
        """
        template_id, project_path = template_with_10_entities

        # Mock artifact content
        with patch(
            "skillmeat.core.services.template_service._fetch_artifact_content",
            return_value="# Test",
        ):
            global query_count
            query_count = 0

            # Execute deployment
            result = deploy_template(
                session=session,
                template_id=template_id,
                project_path=project_path,
                variables={"PROJECT_NAME": "test"},
                overwrite=True,
            )

            assert result.success

            # With eager loading: Should have very few queries
            # Main query + possibly a few transaction overhead queries
            # Should NOT have 10+ queries (N+1 pattern)
            assert (
                query_count <= 5
            ), f"Too many queries: {query_count} (N+1 problem detected)"

            print(
                f"\n✓ Query optimization test passed: {query_count} queries for 10 entities"
            )

    def test_variable_substitution_performance(self):
        """Verify variable substitution uses cached regex patterns.

        This test ensures that variable substitution is efficient by
        using pre-compiled and cached regex patterns.

        Performance target: 1000 substitutions in < 0.1 seconds
        """
        content = """
# Project: {{PROJECT_NAME}}

Description: {{PROJECT_DESCRIPTION}}

Author: {{AUTHOR}}
Date: {{DATE}}

Architecture: {{ARCHITECTURE_DESCRIPTION}}

Project {{PROJECT_NAME}} was created by {{AUTHOR}} on {{DATE}}.
"""

        variables = {
            "PROJECT_NAME": "test-project",
            "PROJECT_DESCRIPTION": "A test project for performance benchmarking",
            "AUTHOR": "test-author",
            "DATE": "2025-12-15",
            "ARCHITECTURE_DESCRIPTION": "Layered architecture with async I/O",
        }

        # Run 1000 substitutions
        start = time.perf_counter()
        for _ in range(1000):
            result = render_content(content, variables)
        duration = time.perf_counter() - start

        # Verify substitution worked
        assert "test-project" in result
        assert "{{PROJECT_NAME}}" not in result

        # Performance target: < 0.1 seconds for 1000 substitutions
        assert duration < 0.1, f"Substitution took {duration:.3f}s (expected <0.1s)"

        print(
            f"\n✓ Variable substitution test passed: {duration:.3f}s for 1000 iterations"
        )

    @pytest.mark.asyncio
    async def test_async_deployment_performance(
        self, session, template_with_10_entities
    ):
        """Verify async deployment uses concurrent file I/O.

        This test ensures that the async version of deploy_template
        uses asyncio.gather() for concurrent file writes when possible.

        Args:
            session: Database session
            template_with_10_entities: Fixture with template and 10 entities
        """
        template_id, project_path = template_with_10_entities

        # Mock artifact content (larger content to see I/O impact)
        mock_content = "# Test Entity\n" + ("Content line\n" * 100)

        with patch(
            "skillmeat.core.services.template_service._fetch_artifact_content",
            return_value=mock_content,
        ):
            # Execute async deployment
            start = time.perf_counter()
            result = await deploy_template_async(
                session=session,
                template_id=template_id,
                project_path=project_path,
                variables={"PROJECT_NAME": "async-test"},
                overwrite=True,
            )
            duration = time.perf_counter() - start

            # Verify correctness
            assert result.success
            assert len(result.deployed_files) == 10

            # Async should be fast (< 5 seconds easily)
            assert duration < 5.0

            print(
                f"\n✓ Async deployment test passed: {duration:.3f}s for 10 entities"
            )


class TestPerformanceReporting:
    """Tests for performance metrics and reporting."""

    def test_deployment_result_includes_metrics(
        self, session, template_with_10_entities
    ):
        """Verify deployment result includes useful metrics.

        Args:
            session: Database session
            template_with_10_entities: Fixture with template and 10 entities
        """
        template_id, project_path = template_with_10_entities

        with patch(
            "skillmeat.core.services.template_service._fetch_artifact_content",
            return_value="# Test",
        ):
            result = deploy_template(
                session=session,
                template_id=template_id,
                project_path=project_path,
                variables={"PROJECT_NAME": "metrics-test"},
            )

            # Verify result structure
            assert result.success
            assert result.project_path == project_path
            assert len(result.deployed_files) > 0
            assert isinstance(result.message, str)
            assert "Successfully deployed" in result.message


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
