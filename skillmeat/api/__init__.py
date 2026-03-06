"""SkillMeat API package.

This package provides the FastAPI-based web service layer for SkillMeat.
It exposes REST endpoints for managing collections, artifacts, and integrations.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server import app, create_app

__all__ = ["app", "create_app"]


def __getattr__(name: str):
    if name in ("app", "create_app"):
        from .server import app, create_app

        globals()["app"] = app
        globals()["create_app"] = create_app
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
