"""SkillMeat Web Interface and Server Management.

This module provides the Next.js web application and server management
tools for SkillMeat's web interface.
"""

from .doctor import WebDoctor, run_doctor
from .manager import WebManager, check_prerequisites
from .requirements import RequirementsChecker, VersionInfo

__all__ = [
    "WebDoctor",
    "run_doctor",
    "WebManager",
    "check_prerequisites",
    "RequirementsChecker",
    "VersionInfo",
]
