"""
Stage handlers package for router.

This package contains handler classes for different conversation stages,
following the Single Responsibility Principle.
"""

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.stage_handlers.readsql_handler import ReadSQLHandler
from src.ai.router.stage_handlers.comparesql_handler import CompareSQLHandler

__all__ = [
    "BaseStageHandler",
    "StageHandlerResult",
    "ReadSQLHandler",
    "CompareSQLHandler",
]
