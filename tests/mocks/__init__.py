"""In-memory mock implementations of SkillMeat repository interfaces.

Use these mocks in tests that need repository DI without touching the
filesystem or a database.  Each mock stores data in plain Python dicts,
exposes a ``reset()`` method to clear state between tests, and accepts
pre-seeded data at construction time.

Example::

    from tests.mocks.repositories import MockArtifactRepository, MockTagRepository

    def test_something():
        repo = MockArtifactRepository(
            initial_artifacts=[
                ArtifactDTO(id="skill:my-skill", name="my-skill", artifact_type="skill"),
            ]
        )
        result = repo.get("skill:my-skill")
        assert result is not None
        assert result.name == "my-skill"
"""

from tests.mocks.repositories import (
    MockArtifactRepository,
    MockCollectionRepository,
    MockDeploymentRepository,
    MockProjectRepository,
    MockSettingsRepository,
    MockTagRepository,
)

__all__ = [
    "MockArtifactRepository",
    "MockProjectRepository",
    "MockCollectionRepository",
    "MockDeploymentRepository",
    "MockTagRepository",
    "MockSettingsRepository",
]
