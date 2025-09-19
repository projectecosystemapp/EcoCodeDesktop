"""
Spec-driven workflow management module.

This module provides comprehensive functionality for managing specification documents,
workflow orchestration, task execution, error handling, validation, and system resilience
in the spec-driven development process.
"""

from .file_manager import FileSystemManager
from .research_service import ResearchService, ResearchContext, ResearchArea, TechnicalFinding
from .error_recovery import ErrorRecoveryService
from .validation_framework import ValidationFramework
from .resilience_service import ResilienceService
from .models import *

__all__ = [
    'FileSystemManager',
    'ResearchService',
    'ResearchContext',
    'ResearchArea',
    'TechnicalFinding',
    'ErrorRecoveryService',
    'ValidationFramework',
    'ResilienceService',
]