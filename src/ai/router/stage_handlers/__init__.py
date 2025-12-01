"""
Stage handlers package for router.

This package contains handler classes for different conversation stages,
following the Single Responsibility Principle.
"""

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.stage_handlers.readsql_handler import ReadSQLHandler
from src.ai.router.stage_handlers.comparesql_handler import CompareSQLHandler
from src.ai.router.stage_handlers.writedata_handler import WriteDataHandler
from src.ai.router.stage_handlers.sendemail_handler import SendEmailHandler

__all__ = [
    "BaseStageHandler",
    "StageHandlerResult",
    "ReadSQLHandler",
    "CompareSQLHandler",
    "WriteDataHandler",
    "SendEmailHandler",
]
