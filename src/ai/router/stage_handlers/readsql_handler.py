"""
ReadSQL flow handler with comprehensive error handling.

Refactored to use Strategy pattern for individual stage handling,
following SOLID principles more strictly.
"""

import logging
from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.stage_handlers.stage_strategy import StageStrategyRegistry
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.errors import ICCBaseError, ErrorHandler
from src.ai.router.global_command_handler import GlobalCommandHandler
from src.ai.router.utils.edit_target_resolver import EditTargetResolver

# Import all ReadSQL strategies
from src.ai.router.stage_handlers.strategies.readsql import (
    AskSqlMethodStrategy,
    NeedNaturalLanguageStrategy,
    NeedUserSqlStrategy,
    ConfirmGeneratedSqlStrategy,
    ConfirmUserSqlStrategy,
    ExecuteSqlStrategy,
    ShowResultsStrategy,
    NeedWriteOrEmailStrategy,
)

logger = logging.getLogger(__name__)


class ReadSQLHandler(BaseStageHandler):
    """
    Handler for ReadSQL workflow stages using Strategy pattern.
    
    Refactored to follow SOLID principles:
    - Single Responsibility: Delegates to strategies, only orchestrates
    - Open/Closed: Easy to add new stages without modifying handler
    - Liskov Substitution: All strategies are interchangeable
    - Interface Segregation: Each strategy has focused interface
    - Dependency Inversion: Depends on strategy abstraction
    """
    
    def __init__(self, sql_agent=None, job_agent=None):
        """
        Initialize ReadSQL handler with strategy registry.
        
        Args:
            sql_agent: SQL agent for query generation (optional)
            job_agent: Job agent for parameter gathering (optional)
        """
        self.sql_agent = sql_agent
        self.job_agent = job_agent
        
        # Initialize strategy registry
        self.strategy_registry = StageStrategyRegistry()
        self._register_strategies()
    
    def _register_strategies(self):
        """Register all ReadSQL stage strategies."""
        # Register each stage with its corresponding strategy
        self.strategy_registry.register(Stage.ASK_SQL_METHOD, AskSqlMethodStrategy())
        self.strategy_registry.register(Stage.NEED_NATURAL_LANGUAGE, NeedNaturalLanguageStrategy(self.sql_agent))
        self.strategy_registry.register(Stage.NEED_USER_SQL, NeedUserSqlStrategy())
        self.strategy_registry.register(Stage.CONFIRM_GENERATED_SQL, ConfirmGeneratedSqlStrategy())
        self.strategy_registry.register(Stage.CONFIRM_USER_SQL, ConfirmUserSqlStrategy())

        # Create ExecuteSqlStrategy instance (needed for confirmation callback)
        execute_strategy = ExecuteSqlStrategy(self.job_agent)
        self.strategy_registry.register(Stage.EXECUTE_SQL, execute_strategy)

        # Register confirmation strategy with execution callback
        from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
        self.strategy_registry.register(
            Stage.CONFIRM_READ_SQL_JOB,
            ConfirmJobStrategy(
                job_type="read_sql",
                execution_callback=lambda m: execute_strategy._execute_read_sql_job(m, m.gathered_params)
            )
        )

        self.strategy_registry.register(Stage.SHOW_RESULTS, ShowResultsStrategy())
        self.strategy_registry.register(Stage.NEED_WRITE_OR_EMAIL, NeedWriteOrEmailStrategy())

        # Confirmation stage (NEW - shows summary before execution)
        from src.ai.router.stage_handlers.strategies.common.confirm_job import ConfirmJobStrategy
        self.strategy_registry.register(Stage.CONFIRM_READ_SQL_JOB, ConfirmJobStrategy(job_type="read_sql"))
    
    def can_handle(self, stage: Stage) -> bool:
        """Check if this handler can process the given stage."""
        return self.strategy_registry.has_strategy(stage)
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """
        Process the ReadSQL stage using registered strategy.

        This method demonstrates the Strategy pattern:
        - Looks up the appropriate strategy for the current stage
        - Delegates execution to that strategy
        - Handles errors gracefully
        """
        logger.info(f"ReadSQLHandler: Processing stage {memory.stage.value}")

        try:
            # Check for global commands first (back, reset, edit, review)
            global_cmd = GlobalCommandHandler.check_global_command(memory, user_input)

            if global_cmd == "reset":
                result = GlobalCommandHandler.handle_reset(memory)
                return self._create_result(
                    memory,
                    result["message"],
                    result.get("transition_to")
                )

            elif global_cmd == "back":
                result = GlobalCommandHandler.handle_back(memory)

                # If we transitioned to a new stage, re-run handler with empty input to trigger that stage's prompt
                if result.get("transition_to"):
                    memory.stage = result["transition_to"]
                    logger.info(f"Re-running handler after back to stage: {memory.stage.value}")
                    return await self.handle(memory, "")  # Re-run with empty input
                else:
                    # No transition - just show the message
                    return self._create_result(memory, result["message"])

            elif global_cmd == "review":
                result = GlobalCommandHandler.handle_review(memory)
                return self._create_result(memory, result["message"])

            elif global_cmd == "edit":
                edit_resolver = EditTargetResolver()
                result = GlobalCommandHandler.handle_edit(memory, user_input, edit_resolver)
                return self._create_result(
                    memory,
                    result["message"],
                    result.get("transition_to")
                )

            # Get strategy for current stage
            strategy = self.strategy_registry.get_strategy(memory.stage)

            if strategy is None:
                logger.error(f"No strategy found for stage {memory.stage.value}")
                return self._create_result(
                    memory,
                    f"Unhandled stage in ReadSQL flow: {memory.stage.value}",
                    is_error=True
                )

            # Delegate to strategy with automatic help detection
            return await strategy.handle_with_help(memory, user_input)

        except ICCBaseError as e:
            logger.error(f"ICC error in ReadSQL handler: {e}")
            return self._create_error_result(memory, e)
        except Exception as e:
            logger.error(f"Unexpected error in ReadSQL handler: {type(e).__name__}: {e}", exc_info=True)
            return self._create_error_result(
                memory, e,
                context={"stage": memory.stage.value},
                fallback_message="An error occurred while processing your request. Please try again."
            )
