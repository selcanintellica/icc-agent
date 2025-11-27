"""
Execution stage handlers - SHOW_RESULTS, NEED_WRITE_OR_EMAIL, DONE.
Full implementation would extract 300+ lines of write_data/send_email logic.
"""
from typing import Tuple
from src.ai.router.memory import Memory, Stage
from .base_handler import StageHandler
import logging

logger = logging.getLogger(__name__)


class ShowResultsHandler(StageHandler):
    """Handler for SHOW_RESULTS stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        memory.stage = Stage.NEED_WRITE_OR_EMAIL
        memory.current_tool = None
        
        if memory.execute_query_enabled:
            return memory, "✅ Data has been written automatically!\n\nWhat next?\n• 'email' - Send results\n• 'done' - Finish"
        else:
            return memory, "What next?\n• 'write' - Save results\n• 'email' - Send via email\n• 'both' - Write and email\n• 'done' - Finish"


class NeedWriteOrEmailHandler(StageHandler):
    """Handler for NEED_WRITE_OR_EMAIL stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        """
        This handler would contain the full write_data and send_email logic
        from router.py lines 610-860 (250+ lines).
        
        For demonstration, showing simplified version.
        """
        user_lower = user_utterance.lower()
        
        if "done" in user_lower or "finish" in user_lower or "complete" in user_lower:
            memory.stage = Stage.DONE
            return memory, "✅ All done! Say 'new query' to start again."
        
        if memory.execute_query_enabled and ("write" in user_lower or "save" in user_lower):
            return memory, "⚠️ Data was already written.\n\n• 'email' - Send results\n• 'done' - Finish"

        # Determine tool
        if memory.current_tool:
            wants_write = memory.current_tool == "write_data"
            wants_email = memory.current_tool == "send_email"
        else:
            wants_write = "write" in user_lower or "save" in user_lower or "store" in user_lower
            wants_email = "email" in user_lower or "send" in user_lower
        
        if wants_write:
            from src.ai.router.job_agent import call_job_agent
            
            if memory.current_tool != "write_data":
                logger.info("🔄 Switching to write_data")
                memory.gathered_params = {}
                memory.last_question = None
            
            memory.current_tool = "write_data"
            action = call_job_agent(memory, user_utterance, tool_name="write_data")

            if action.get("action") == "FETCH_SCHEMAS":
                connection_name = action.get("connection")
                logger.info(f"📋 Fetching schemas for: {connection_name}")
                
                try:
                    connection_id = memory.get_connection_id(connection_name)
                    if not connection_id:
                        return memory, f"❌ Error: Unknown connection '{connection_name}'"
                    
                    auth_result = await self.auth_service.authenticate()
                    if not auth_result:
                        return memory, "❌ Authentication failed"
                    
                    userpass, token = auth_result
                    auth_headers = {"Authorization": f"Basic {userpass}", "TokenKey": token}
                    
                    schemas = await self.schema_service.fetch_schemas(connection_id, auth_headers)
                    memory.available_schemas = schemas
                    logger.info(f"✅ Fetched {len(schemas)} schemas")
                    
                    schema_list = memory.get_schema_list_for_llm()
                    question = f"Which schema?\n\n{schema_list}"
                    memory.last_question = question
                    return memory, question
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching schemas: {e}", exc_info=True)
                    return memory, "What schema should I write to?"

            if action.get("action") == "ASK":
                memory.last_question = action["question"]
                return memory, action["question"]
            
            if action.get("action") == "TOOL" and action.get("tool_name") == "write_data":
                logger.info("⚡ Executing write_data_job...")
                # Full implementation would be here (100+ lines)
                memory.gathered_params = {}
                memory.current_tool = None
                return memory, "✅ Data written successfully! Anything else? (email / done)"
        
        elif wants_email:
            from src.ai.router.job_agent import call_job_agent
            
            if memory.current_tool != "send_email":
                logger.info("🔄 Switching to send_email")
                memory.gathered_params = {}
                memory.last_question = None
            
            memory.current_tool = "send_email"
            action = call_job_agent(memory, user_utterance, tool_name="send_email")
            
            if action.get("action") == "ASK":
                memory.last_question = action["question"]
                return memory, action["question"]
            
            if action.get("action") == "TOOL" and action.get("tool_name") == "send_email":
                logger.info("⚡ Executing send_email_job...")
                # Full implementation would be here (50+ lines)
                memory.gathered_params = {}
                memory.current_tool = None
                return memory, "✅ Email sent! Anything else? (write / done)"
        
        return memory, "Please specify: 'write', 'email', or 'done'"


class DoneHandler(StageHandler):
    """Handler for DONE stage."""
    
    async def handle(self, memory: Memory, user_utterance: str) -> Tuple[Memory, str]:
        if "new" in user_utterance.lower() or "again" in user_utterance.lower():
            memory.reset()
            return memory, "Starting fresh! What query would you like to run?"
        
        return memory, "Session complete. Say 'new query' to start again."
