"""
Parameter Validators - Open/Closed Principle + Single Responsibility
Each validator handles parameter validation for a specific job type.
Easy to add new validators without modifying existing code.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.ai.router.memory import Memory

logger = logging.getLogger(__name__)


class ParameterValidator(ABC):
    """Abstract base class for parameter validators."""
    
    @abstractmethod
    def validate(self, params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """
        Validate parameters for a specific job type.
        
        Args:
            params: Gathered parameters
            memory: Conversation memory
            
        Returns:
            ASK action dict if parameters are missing, None if all present
        """
        pass
    
    def _check_write_count_params(
        self, 
        params: Dict[str, Any], 
        memory: Memory, 
        param_prefix: str = "write_count"
    ) -> Optional[Dict[str, Any]]:
        """
        Check write_count related parameters.
        
        Args:
            params: Current gathered parameters
            memory: Conversation memory
            param_prefix: Prefix for parameter names ('write_count')
            
        Returns:
            ASK action if missing, None if complete
        """
        schema_param = f"{param_prefix}_schema" if param_prefix == "write_count" else f"{param_prefix}_schemas"
        
        if not params.get(schema_param):
            logger.info(f"❌ Missing: {schema_param} (write_count=true)")
            return {
                "action": "ASK",
                "question": "What schema should I write the row count to?"
            }
        if not params.get(f"{param_prefix}_table"):
            logger.info(f"❌ Missing: {param_prefix}_table (write_count=true)")
            return {
                "action": "ASK",
                "question": "What table should I write the row count to?"
            }
        if not params.get(f"{param_prefix}_connection"):
            logger.info(f"❌ Missing: {param_prefix}_connection (write_count=true), suggesting: {memory.connection}")
            return {
                "action": "ASK",
                "question": f"What connection should I use for the row count? (Press enter for '{memory.connection}')"
            }
        
        # If user just pressed enter or said "same", use memory.connection
        if params.get(f"{param_prefix}_connection", "").strip() in ["", "same", "default"]:
            params[f"{param_prefix}_connection"] = memory.connection
            logger.info(f"📝 Using default connection for write_count: {memory.connection}")
        
        return None  # All params present


class ReadSqlValidator(ParameterValidator):
    """Validates parameters for read_sql job."""
    
    def validate(self, params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """Validate read_sql parameters."""
        # Check if we have name parameter
        if not params.get("name"):
            logger.info("❌ Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this read_sql job?"
            }
        
        # Check if we should ask about execute_query
        if "execute_query" not in params:
            logger.info("❓ Asking about execute_query")
            return {
                "action": "ASK",
                "question": "Would you like to save the query results to the database? (yes/no)"
            }
        
        # If execute_query is true, we need additional parameters
        if params.get("execute_query"):
            if not params.get("result_schema"):
                logger.info("❌ Missing: result_schema (execute_query=true)")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the results to?"
                }
            if not params.get("table_name"):
                logger.info("❌ Missing: table_name (execute_query=true)")
                return {
                    "action": "ASK",
                    "question": "What table should I write the results to?"
                }
            if "drop_before_create" not in params:
                logger.info("❓ Asking about drop_before_create")
                return {
                    "action": "ASK",
                    "question": "Should I drop the table before creating it? (yes/no)"
                }
        
        # Check if we should ask about write_count
        if "write_count" not in params:
            logger.info("❓ Asking about write_count")
            return {
                "action": "ASK",
                "question": "Would you like to track the row count of the query results? (yes/no)"
            }
        
        # If write_count is true, we need additional parameters
        if params.get("write_count"):
            result = self._check_write_count_params(params, memory, "write_count")
            if result:
                return result
        
        # All required params present
        logger.info(f"✅ All read_sql params present: {params}")
        return None


class WriteDataValidator(ParameterValidator):
    """Validates parameters for write_data job."""
    
    def validate(self, params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """Validate write_data parameters."""
        if not params.get("name"):
            logger.info("❌ Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this write_data job?"
            }
        if not params.get("table"):
            logger.info("❌ Missing: table")
            return {
                "action": "ASK",
                "question": "What table should I write the data to?"
            }
        
        # Ask user for connection from available dynamic connections
        if not params.get("connection"):
            logger.info("❌ Missing: connection for write_data")
            logger.info(f"📋 Memory has {len(memory.connections)} connections")
            connection_list = memory.get_connection_list_for_llm()
            
            if connection_list and memory.connections:
                return {
                    "action": "ASK",
                    "question": f"Which connection should I use to write the data?\n\nAvailable connections:\n{connection_list}"
                }
            else:
                # Fallback: use the same connection as read_sql
                params["connection"] = memory.connection
                logger.info(f"⚠️ No dynamic connections available, using read_sql connection: {memory.connection}")
        
        # Check if we need to fetch schemas
        if not params.get("schemas"):
            connection_name = params.get("connection")
            if connection_name and not memory.available_schemas:
                # Need to fetch schemas - signal to router
                logger.info(f"📋 Need to fetch schemas for connection: {connection_name}")
                return {
                    "action": "FETCH_SCHEMAS",
                    "connection": connection_name,
                    "question": "Fetching available schemas..."
                }
            elif memory.available_schemas:
                # We have schemas, ask user to choose
                logger.info("❌ Missing: schemas (have cached list)")
                schema_list = memory.get_schema_list_for_llm()
                return {
                    "action": "ASK",
                    "question": f"Which schema should I write the data to?\n\nAvailable schemas:\n{schema_list}"
                }
            else:
                # No connection ID available, ask for schema without list
                logger.info("❌ Missing: schemas (no cached list)")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the data to?"
                }
        
        if not params.get("drop_or_truncate"):
            logger.info("❌ Missing: drop_or_truncate")
            return {
                "action": "ASK",
                "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
            }
        
        # Check if we should ask about write_count
        if "write_count" not in params:
            logger.info("❓ Asking about write_count for write_data")
            return {
                "action": "ASK",
                "question": "Would you like to track the row count for this write operation? (yes/no)"
            }
        
        # If write_count is true, we need additional parameters
        if params.get("write_count"):
            result = self._check_write_count_params(params, memory, "write_count")
            if result:
                return result
        
        # All params present
        logger.info(f"✅ All write_data params present: {params}")
        return None


class SendEmailValidator(ParameterValidator):
    """Validates parameters for send_email job."""
    
    def validate(self, params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """Validate send_email parameters."""
        if not params.get("name"):
            logger.info("❌ Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this email job?"
            }
        if not params.get("to"):
            logger.info("❌ Missing: to")
            return {
                "action": "ASK",
                "question": "Who should I send the email to?"
            }
        if not params.get("subject"):
            logger.info("❌ Missing: subject")
            return {
                "action": "ASK",
                "question": "What should the email subject be?"
            }
        
        # Check for CC only if not already asked
        if "cc" not in params:
            logger.info("❓ Asking for CC (optional)")
            return {
                "action": "ASK",
                "question": "Would you like to add any CC email addresses? (Say 'no' or 'none' to skip, or provide email addresses)"
            }
        
        # Normalize CC: if user said no/none, set to empty string
        cc_value = params.get("cc", "")
        if isinstance(cc_value, str) and cc_value.lower().strip() in ["no", "none", "skip", "n/a"]:
            params["cc"] = ""
            logger.info("📧 CC normalized to empty string (user declined)")
        
        # All required params present
        logger.info(f"✅ All send_email params present: {params}")
        return None


class CompareSqlValidator(ParameterValidator):
    """Validates parameters for compare_sql job."""
    
    def validate(self, params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """Validate compare_sql parameters."""
        if not params.get("first_table_keys"):
            return {
                "action": "ASK",
                "question": "What are the key columns for the first query? (comma separated)"
            }
        if not params.get("second_table_keys"):
            return {
                "action": "ASK",
                "question": "What are the key columns for the second query? (comma separated)"
            }
        
        # Have enough params
        logger.info(f"✅ All compare_sql params present: {params}")
        return None


# Validator registry - makes it easy to add new validators (Open/Closed Principle)
VALIDATORS: Dict[str, ParameterValidator] = {
    "read_sql": ReadSqlValidator(),
    "write_data": WriteDataValidator(),
    "send_email": SendEmailValidator(),
    "compare_sql": CompareSqlValidator(),
}
