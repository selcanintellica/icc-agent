"""
WriteData flow handler.

Handles all stages related to writing query results to database tables following SOLID principles.
"""

import logging
import json
from typing import Dict, Any
from src.ai.router.stage_handlers.base_handler import BaseStageHandler, StageHandlerResult
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.job_agent import call_job_agent
from src.ai.router.utils.connection_fetcher import ConnectionFetcher
from src.ai.toolkits.icc_toolkit import write_data_job
from src.models.natural_language import WriteDataLLMRequest, WriteDataVariables, ColumnSchema

logger = logging.getLogger(__name__)


class WriteDataHandler(BaseStageHandler):
    """
    Handler for WriteData workflow.
    
    Following Single Responsibility Principle - only handles write_data-related operations.
    """
    
    # Define which stages this handler manages
    MANAGED_STAGES = {
        Stage.NEED_WRITE_OR_EMAIL,  # Can be triggered from this stage
    }
    
    def __init__(self, job_agent=None):
        """
        Initialize WriteData handler.
        
        Args:
            job_agent: Job agent for parameter gathering (optional)
        """
        self.job_agent = job_agent
    
    def can_handle(self, stage: Stage) -> bool:
        """
        Check if this handler can process the given stage.
        
        Note: WriteData is typically accessed as a tool after ReadSQL,
        so it checks memory.current_tool in addition to stage.
        """
        return stage in self.MANAGED_STAGES
    
    async def handle(self, memory: Memory, user_input: str) -> StageHandlerResult:
        """Process the WriteData workflow."""
        logger.info(f"📗 WriteDataHandler: Processing write_data request")
        
        # Clear params only when switching from read_sql
        # Check for execute_query (always present in read_sql) but NOT write_data-specific params
        has_read_sql_only_params = (
            "execute_query" in memory.gathered_params and 
            not any(k in memory.gathered_params for k in ["connection", "schemas", "table", "drop_or_truncate"])
        )
        if has_read_sql_only_params:
            logger.info("🔄 Switching from read_sql to write_data, clearing gathered_params")
            memory.gathered_params = {}
            memory.last_question = None
        
        memory.current_tool = "write_data"
        logger.info("📝 Processing write_data request...")
        
        # Get action from job agent
        action = call_job_agent(memory, user_input, tool_name="write_data")
        
        # Handle different action types
        if action.get("action") == "FETCH_CONNECTIONS":
            return await self._fetch_connections(memory)
        
        if action.get("action") == "FETCH_SCHEMAS":
            return await self._fetch_schemas(memory, action.get("connection"))
        
        if action.get("action") == "ASK":
            memory.last_question = action["question"]
            return self._create_result(memory, action["question"])
        
        if action.get("action") == "TOOL" and action.get("tool_name") == "write_data":
            return await self._execute_write_data_job(memory, action.get("params", {}))
        
        return self._create_result(memory, "Please provide write_data parameters.")
    
    async def _fetch_connections(self, memory: Memory) -> StageHandlerResult:
        """Fetch all available connections for write_data."""
        result = await ConnectionFetcher.fetch_connections(memory)
        
        if result["success"]:
            question = ConnectionFetcher.create_connection_question(memory, purpose="main")
            memory.last_question = question
            return self._create_result(memory, question)
        else:
            return self._create_result(
                memory,
                f"❌ Error: {result['message']}\nPlease try again."
            )
    
    async def _fetch_schemas(self, memory: Memory, connection_name: str) -> StageHandlerResult:
        """Fetch schemas for the selected connection."""
        result = await ConnectionFetcher.fetch_schemas(connection_name, memory)
        
        if result["success"]:
            # Determine purpose
            params = memory.gathered_params
            if params.get("write_count") and not params.get("write_count_schemas"):
                purpose = "write_count"
                param_name = "write_count_schemas"
                question_text = "Which schema should I write the row count to?"
            else:
                purpose = "data"
                param_name = "schemas"
                question_text = "Which schema should I write the data to?"
            
            # Return special format for UI to show dropdown
            response = f"SCHEMA_DROPDOWN:{json.dumps({'schemas': memory.available_schemas, 'param_name': param_name, 'question': question_text})}"
            memory.last_question = question_text
            return self._create_result(memory, response)
        else:
            return self._create_result(
                memory,
                f"❌ Error: {result['message']}\nPlease try again."
            )
    
    async def _execute_write_data_job(self, memory: Memory, params: Dict[str, Any]) -> StageHandlerResult:
        """Execute write_data job to write results to database table."""
        logger.info("⚡ Executing write_data_job...")
        
        try:
            # Get connection ID
            connection_name = params.get("connection", memory.connection)
            connection_id = memory.get_connection_id(connection_name)
            
            if not connection_id:
                from src.utils.connections import get_connection_id
                connection_id = get_connection_id(connection_name)
                if not connection_id:
                    return self._create_result(
                        memory,
                        f"❌ Error: Unknown connection '{connection_name}'."
                    )
            
            # Prepare parameters
            table_name = params.get("table", "output_table")
            drop_or_truncate = params.get("drop_or_truncate", "INSERT").upper()
            
            if drop_or_truncate not in ["DROP", "TRUNCATE", "INSERT"]:
                drop_or_truncate = "INSERT"
            
            columns = [ColumnSchema(columnName=col) for col in (memory.last_columns or [])]
            schemas = params.get("schemas", memory.schema)
            write_count = params.get("write_count", False)
            
            # Create WriteDataVariables
            write_data_vars = WriteDataVariables(
                data_set=memory.last_job_id,
                data_set_job_name=memory.last_job_name,
                data_set_folder=memory.last_job_folder,
                columns=columns,
                add_columns=[],
                connection=connection_id,
                schemas=schemas,
                table=table_name,
                drop_or_truncate=drop_or_truncate,
                write_count=write_count
            )
            
            # Handle write_count parameters if enabled
            if write_count:
                write_count_conn_name = params.get("write_count_connection", memory.connection)
                write_count_conn_id = memory.get_connection_id(write_count_conn_name)
                
                if not write_count_conn_id:
                    from src.utils.connections import get_connection_id as get_conn_id_static
                    write_count_conn_id = get_conn_id_static(write_count_conn_name)
                    if not write_count_conn_id:
                        return self._create_result(
                            memory,
                            f"❌ Error: Unknown connection '{write_count_conn_name}' for write_count."
                        )
                
                write_data_vars.write_count_connection = write_count_conn_id
                write_data_vars.write_count_schemas = params.get("write_count_schemas")
                write_data_vars.write_count_table = params.get("write_count_table")
            
            # Create request and execute job
            request = WriteDataLLMRequest(
                rights={"owner": "184431757886694"},
                props={"active": "true", "name": params.get("name", "WriteData_Job"), "description": ""},
                variables=[write_data_vars]
            )
            
            result = await write_data_job(request)
            logger.info(f"📊 write_data_job result: {json.dumps(result, indent=2, default=str)}")
            
            # Track output table info for send_email query generation
            memory.output_table_info = {
                "schema": schemas,
                "table": table_name
            }
            logger.info(f"📝 Set output_table_info from WriteData: {memory.output_table_info}")
            
            # Clean up memory
            memory.gathered_params = {}
            memory.current_tool = None
            memory.last_question = None
            
            return self._create_result(
                memory,
                f"✅ Data written successfully to table '{table_name}' in {schemas} schema!\nAnything else? (email / done)"
            )
        
        except Exception as e:
            logger.error(f"❌ Error in write_data: {str(e)}", exc_info=True)
            return self._create_result(
                memory,
                f"❌ Error: {str(e)}\nPlease try again."
            )
