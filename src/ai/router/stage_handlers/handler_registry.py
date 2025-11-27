"""
Handler registry - maps Stage enum to handler classes.
Implements Open/Closed Principle - add new stages without modifying router.
"""
from src.ai.router.memory import Stage
from .common_handlers import StartHandler, AskJobTypeHandler
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


# Registry mapping Stage enum to handler class
# To add a new stage: Just add it here! No modification to router needed. (OCP)
HANDLER_REGISTRY = {
    # Common stages
    Stage.START: StartHandler,
    Stage.ASK_JOB_TYPE: AskJobTypeHandler,
    
    # ReadSQL flow
    Stage.ASK_SQL_METHOD: AskSqlMethodHandler,
    Stage.NEED_NATURAL_LANGUAGE: NeedNaturalLanguageHandler,
    Stage.NEED_USER_SQL: NeedUserSqlHandler,
    Stage.CONFIRM_GENERATED_SQL: ConfirmGeneratedSqlHandler,
    Stage.CONFIRM_USER_SQL: ConfirmUserSqlHandler,
    Stage.EXECUTE_SQL: ExecuteSqlHandler,
    
    # CompareSQL flow
    Stage.ASK_FIRST_SQL_METHOD: AskFirstSqlMethodHandler,
    Stage.NEED_FIRST_NATURAL_LANGUAGE: NeedFirstNaturalLanguageHandler,
    Stage.NEED_FIRST_USER_SQL: NeedFirstUserSqlHandler,
    Stage.CONFIRM_FIRST_GENERATED_SQL: ConfirmFirstGeneratedSqlHandler,
    Stage.CONFIRM_FIRST_USER_SQL: ConfirmFirstUserSqlHandler,
    Stage.ASK_SECOND_SQL_METHOD: AskSecondSqlMethodHandler,
    Stage.NEED_SECOND_NATURAL_LANGUAGE: NeedSecondNaturalLanguageHandler,
    Stage.NEED_SECOND_USER_SQL: NeedSecondUserSqlHandler,
    Stage.CONFIRM_SECOND_GENERATED_SQL: ConfirmSecondGeneratedSqlHandler,
    Stage.CONFIRM_SECOND_USER_SQL: ConfirmSecondUserSqlHandler,
    Stage.ASK_AUTO_MATCH: AskAutoMatchHandler,
    Stage.WAITING_MAP_TABLE: WaitingMapTableHandler,
    Stage.ASK_REPORTING_TYPE: AskReportingTypeHandler,
    Stage.ASK_COMPARE_SCHEMA: AskCompareSchemaHandler,
    Stage.ASK_COMPARE_TABLE_NAME: AskCompareTableNameHandler,
    Stage.ASK_COMPARE_JOB_NAME: AskCompareJobNameHandler,
    Stage.EXECUTE_COMPARE_SQL: AskCompareJobNameHandler,  # Redirect
    
    # Execution stages
    Stage.SHOW_RESULTS: ShowResultsHandler,
    Stage.NEED_WRITE_OR_EMAIL: NeedWriteOrEmailHandler,
    Stage.DONE: DoneHandler,
}
