"""Update flow integration tests.

This module re-exports integration tests from tests/integration/test_update_flow.py
for CI/CD discovery and execution.
"""

# Re-export all test classes and fixtures for CI discovery
from tests.integration.test_update_flow import (  # noqa: F401
    TestUpdateFlowGithubSuccess,
    TestUpdateFlowNetworkFailure,
    TestUpdateFlowLocalModificationsPrompt,
    TestUpdateFlowStrategyEnforcement,
    TestUpdateFlowLockManifestConsistency,
    temp_skillmeat_dir,
    config,
    collection_mgr,
    artifact_mgr,
    initialized_collection,
    github_artifact,
)

__all__ = [
    "TestUpdateFlowGithubSuccess",
    "TestUpdateFlowNetworkFailure",
    "TestUpdateFlowLocalModificationsPrompt",
    "TestUpdateFlowStrategyEnforcement",
    "TestUpdateFlowLockManifestConsistency",
    "temp_skillmeat_dir",
    "config",
    "collection_mgr",
    "artifact_mgr",
    "initialized_collection",
    "github_artifact",
]
