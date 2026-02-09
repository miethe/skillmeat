"""Template deployment profile rewrite tests."""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Artifact, Collection, Project, ProjectTemplate, TemplateEntity, create_db_engine, create_tables
from skillmeat.core.services.template_service import deploy_template


def test_template_deploy_rewrites_profile_root_for_selected_profile(tmp_path):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    create_tables(db_path)
    engine = create_db_engine(db_path)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()

    try:
        template_id = uuid.uuid4().hex
        artifact_id = uuid.uuid4().hex
        session.add(
            Project(
                id="ctx_project_global",
                name="Context Entities",
                path=str((tmp_path / "context-entities").resolve()),
                status="active",
            )
        )
        session.add(
            Collection(
                id="default",
                name="Default",
                description="Default collection",
            )
        )
        session.add(
            ProjectTemplate(
                id=template_id,
                name="profile-template",
                description="template with context entity",
                collection_id="default",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        session.add(
            Artifact(
                id=artifact_id,
                project_id="ctx_project_global",
                name="api-rule",
                type="rule_file",
                path_pattern=".claude/rules/api.md",
                content="# API Rule",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        session.add(
            TemplateEntity(
                template_id=template_id,
                artifact_id=artifact_id,
                deploy_order=0,
                required=True,
            )
        )
        session.commit()

        project_path = tmp_path / "profile-project"
        project_path.mkdir(parents=True, exist_ok=True)

        with patch(
            "skillmeat.core.services.template_service._fetch_artifact_content",
            return_value="# API Rule",
        ):
            result = deploy_template(
                session=session,
                template_id=template_id,
                project_path=str(project_path),
                variables={"PROJECT_NAME": "profile-project"},
                deployment_profile_id="codex",
                overwrite=True,
            )

        assert result.success is True
        assert (project_path / ".codex" / "rules" / "api.md").exists()
        assert not (project_path / ".claude" / "rules" / "api.md").exists()
    finally:
        session.close()
        engine.dispose()
        Path(db_path).unlink(missing_ok=True)
