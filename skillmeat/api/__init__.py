"""SkillMeat API package.

This package provides the FastAPI-based web service layer for SkillMeat.
It exposes REST endpoints for managing collections, artifacts, and integrations.
"""

from .server import app, create_app

__all__ = ["app", "create_app"]
