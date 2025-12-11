"""
CompareSQL flow handler using Strategy pattern.

Handles all stages related to the CompareSQL workflow following SOLID principles.
"""

import logging

from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.stage_handlers.stage_strategy import StageStrategyRegistry
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.errors import ICCBaseError

# Import all CompareSQL strategies
from src.ai.router.stage_handlers.strategies.comparesql import (
    AskFirstSQLMethodStrategy,
    NeedFirstNaturalLanguageStrategy,
    NeedFirstUserSQLStrategy,
    ConfirmFirstSQLStrategy,
    AskSecondSQLMethodStrategy,
    NeedSecondNaturalLanguageStrategy,
    NeedSecondUserSQLStrategy,
    ConfirmSecondSQLStrategy,
    AskAutoMatchStrategy,
    WaitingMapTableStrategy,
    AskReportingTypeStrategy,
    GatherCompareParamsStrategy,
    AskCompareSchemaStrategy,
    AskCompareTableNameStrategy,
    AskCompareJobNameStrategy,
    ExecuteCompareSQLStrategy,
)

logger = logging.getLogger(__name__)


class CompareSQLHandler(BaseStageHandler):
    """
    Handler for CompareSQL workflow stages using Strategy pattern.
    
    Following Single Responsibility Principle - only handles CompareSQL stage routing.
    Business logic delegated to individual strategy classes.
    """
    
    MANAGED_STAGES = {
        Stage.ASK_FIRST_SQL_METHOD,
        Stage.NEED_FIRST_NATURAL_LANGUAGE,
        Stage.NEED_FIRST_USER_SQL,
        Stage.CONFIRM_FIRST_GENERATED_SQL,
        Stage.CONFIRM_FIRST_USER_SQL,
        Stage.ASK_SECOND_SQL_METHOD,
        Stage.NEED_SECOND_NATURAL_LANGUAGE,
        Stage.NEED_SECOND_USER_SQL,
        Stage.CONFIRM_SECOND_GENERATED_SQL,
        Stage.CONFIRM_SECOND_USER_SQL,
        Stage.ASK_AUTO_MATCH,
        Stage.WAITING_MAP_TABLE,
        Stage.ASK_REPORTING_TYPE,
        Stage.GATHER_COMPARE_PARAMS,
        Stage.ASK_COMPARE_SCHEMA,
        Stage.ASK_COMPARE_TABLE_NAME,
        Stage.ASK_COMPARE_JOB_NAME,
        Stage.EXECUTE_COMPARE_SQL,
    }
    
    def __init__(self, sql_agent=None, job_agent=None):
        """Initialize CompareSQL handler and register strategies."""
        self.sql_agent = sql_agent
        self.job_agent = job_agent
        self._registry = StageStrategyRegistry()
        self._register_strategies()
    
    def _register_strategies(self):
        """Register all CompareSQL stage strategies."""
        # First SQL method and generation
        self._registry.register(Stage.ASK_FIRST_SQL_METHOD, AskFirstSQLMethodStrategy())
        self._registry.register(Stage.NEED_FIRST_NATURAL_LANGUAGE, NeedFirstNaturalLanguageStrategy())
        self._registry.register(Stage.NEED_FIRST_USER_SQL, NeedFirstUserSQLStrategy())
        
        # First SQL confirmation (handles both generated and user SQL)
        confirm_first = ConfirmFirstSQLStrategy()
        self._registry.register(Stage.CONFIRM_FIRST_GENERATED_SQL, confirm_first)
        self._registry.register(Stage.CONFIRM_FIRST_USER_SQL, confirm_first)
        
        # Second SQL method and generation
        self._registry.register(Stage.ASK_SECOND_SQL_METHOD, AskSecondSQLMethodStrategy())
        self._registry.register(Stage.NEED_SECOND_NATURAL_LANGUAGE, NeedSecondNaturalLanguageStrategy())
        self._registry.register(Stage.NEED_SECOND_USER_SQL, NeedSecondUserSQLStrategy())
        
        # Second SQL confirmation (handles both generated and user SQL)
        confirm_second = ConfirmSecondSQLStrategy()
        self._registry.register(Stage.CONFIRM_SECOND_GENERATED_SQL, confirm_second)
        self._registry.register(Stage.CONFIRM_SECOND_USER_SQL, confirm_second)
        
        # Column mapping and configuration
        self._registry.register(Stage.ASK_AUTO_MATCH, AskAutoMatchStrategy())
        self._registry.register(Stage.WAITING_MAP_TABLE, WaitingMapTableStrategy())
        self._registry.register(Stage.ASK_REPORTING_TYPE, AskReportingTypeStrategy())

        # Job parameters and execution (consolidated with job agent)
        self._registry.register(Stage.GATHER_COMPARE_PARAMS, GatherCompareParamsStrategy())

        # Legacy stages (kept for backward compatibility)
        self._registry.register(Stage.ASK_COMPARE_SCHEMA, AskCompareSchemaStrategy())
        self._registry.register(Stage.ASK_COMPARE_TABLE_NAME, AskCompareTableNameStrategy())
        self._registry.register(Stage.ASK_COMPARE_JOB_NAME, AskCompareJobNameStrategy())
        self._registry.register(Stage.EXECUTE_COMPARE_SQL, ExecuteCompareSQLStrategy())
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the CompareSQL stage by delegating to appropriate strategy."""
        logger.info(f"CompareSQLHandler: Processing stage {memory.stage.value}")
        
        try:
            # Get strategy for current stage
            strategy = self._registry.get_strategy(memory.stage)
            
            if strategy:
                # Delegate to strategy
                return await strategy.handle_with_help(memory, user_input)
            else:
                logger.warning(f"No strategy registered for stage {memory.stage.value}")
                return self._create_result(memory, "Unhandled stage in CompareSQL flow")
            
        except ICCBaseError as e:
            logger.error(f"ICC error in CompareSQL handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in CompareSQL handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while processing your request. Please try again."
            )
