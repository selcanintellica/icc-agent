"""
Stage handlers package - each handler is responsible for one stage.
Implements Single Responsibility Principle (SRP) and Open/Closed Principle (OCP).
"""

from .base_handler import StageHandler
from .read_sql_handlers import (
    AskSqlMethodHandler,
    NeedNaturalLanguageHandler,
    NeedUserSqlHandler,
    ConfirmGeneratedSqlHandler,
    ConfirmUserSqlHandler,
    ExecuteSqlHandler,
)
from .compare_sql_handlers import (
    AskFirstSqlMethodHandler,
    NeedFirstNaturalLanguageHandler,
    NeedFirstUserSqlHandler,
    ConfirmFirstGeneratedSqlHandler,
    ConfirmFirstUserSqlHandler,
    AskSecondSqlMethodHandler,
    NeedSecondNaturalLanguageHandler,
    NeedSecondUserSqlHandler,
    ConfirmSecondGeneratedSqlHandler,
    ConfirmSecondUserSqlHandler,
    AskAutoMatchHandler,
    WaitingMapTableHandler,
    AskReportingTypeHandler,
    AskCompareSchemaHandler,
    AskCompareTableNameHandler,
    AskCompareJobNameHandler,
)
from .execution_handlers import (
    ShowResultsHandler,
    NeedWriteOrEmailHandler,
    DoneHandler,
)
from .common_handlers import (
    StartHandler,
    AskJobTypeHandler,
)
from .handler_registry import HANDLER_REGISTRY

__all__ = [
    "StageHandler",
    "HANDLER_REGISTRY",
    # Common
    "StartHandler",
    "AskJobTypeHandler",
    # ReadSQL
    "AskSqlMethodHandler",
    "NeedNaturalLanguageHandler",
    "NeedUserSqlHandler",
    "ConfirmGeneratedSqlHandler",
    "ConfirmUserSqlHandler",
    "ExecuteSqlHandler",
    # CompareSQL
    "AskFirstSqlMethodHandler",
    "NeedFirstNaturalLanguageHandler",
    "NeedFirstUserSqlHandler",
    "ConfirmFirstGeneratedSqlHandler",
    "ConfirmFirstUserSqlHandler",
    "AskSecondSqlMethodHandler",
    "NeedSecondNaturalLanguageHandler",
    "NeedSecondUserSqlHandler",
    "ConfirmSecondGeneratedSqlHandler",
    "ConfirmSecondUserSqlHandler",
    "AskAutoMatchHandler",
    "WaitingMapTableHandler",
    "AskReportingTypeHandler",
    "AskCompareSchemaHandler",
    "AskCompareTableNameHandler",
    "AskCompareJobNameHandler",
    # Execution
    "ShowResultsHandler",
    "NeedWriteOrEmailHandler",
    "DoneHandler",
]
