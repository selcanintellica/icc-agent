"""
Common stage handlers - START and ASK_JOB_TYPE stages.
"""
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from .base_handler import StageHandler
import logging

logger = logging.getLogger(__name__)


class StartHandler(StageHandler):
    """Handler for START stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        memory.stage = Stage.ASK_JOB_TYPE
        return memory, "How would you like to proceed? 'readsql' or 'comparesql'?"


class AskJobTypeHandler(StageHandler):
    """Handler for ASK_JOB_TYPE stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        user_lower = user_utterance.lower()

        if "compare" in user_lower:
            logger.info("📝 User chose: COMPARE SQL")
            memory.job_type = "comparesql"
            memory.stage = Stage.ASK_FIRST_SQL_METHOD
            return memory, "For the FIRST query, how would you like to proceed?\n• Type 'create' - I'll generate SQL\n• Type 'provide' - You provide the SQL"

        elif "read" in user_lower:
            logger.info("📝 User chose: READ SQL")
            memory.job_type = "readsql"
            memory.stage = Stage.ASK_SQL_METHOD
            return memory, "How would you like to proceed?\n• Type 'create' - I'll generate SQL from your natural language\n• Type 'provide' - You provide the SQL query directly"

        else:
            return memory, "Please choose: 'readsql' or 'comparesql'"
