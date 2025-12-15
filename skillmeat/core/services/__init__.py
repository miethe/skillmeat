"""Core services package for SkillMeat.

This package contains business logic services that are used by API routers
and other application layers.
"""

from skillmeat.core.services.template_service import (
    DeploymentResult,
    deploy_template,
    render_content,
    validate_variables,
    ALLOWED_VARIABLES,
)

__all__ = [
    "DeploymentResult",
    "deploy_template",
    "render_content",
    "validate_variables",
    "ALLOWED_VARIABLES",
]
