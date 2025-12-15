"""
Parameter validation for job agents.

This module provides parameter validation following the Single Responsibility Principle.
"""

import logging
from typing import Dict, Any, Optional, List
from src.ai.router.memory import Memory

logger = logging.getLogger(__name__)


class ParameterValidator:
    """
    Validates parameters for different job types.
    
    Following Single Responsibility Principle - only responsible for validation.
    """
    
    @staticmethod
    def validate_read_sql_params(params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """
        Validate read_sql parameters.
        
        Args:
            params: Current gathered parameters
            memory: Conversation memory
            
        Returns:
            Dict with ASK action if missing parameters, None if all valid
        """
        if not params.get("name"):
            logger.debug("Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this read_sql job?"
            }
        
        # Check execute_query - treat empty string as missing
        execute_query_value = params.get("execute_query")
        if execute_query_value is None or execute_query_value == "":
            logger.debug("Asking about execute_query")
            return {
                "action": "ASK",
                "question": "Would you like to save the query results to the database? (yes/no)"
            }
        
        if params.get("execute_query"):
            # Need result_schema (fetch if needed for the SAME connection as query)
            if not params.get("result_schema"):
                # Use the same connection as the SQL query (from UI dropdown)
                connection_name = memory.connection
                if connection_name and not memory.available_schemas:
                    logger.debug(f"Need to fetch schemas for connection: {connection_name}")
                    memory.available_schemas = []  # Clear cached schemas before fetching
                    return {
                        "action": "FETCH_SCHEMAS",
                        "connection": connection_name,
                        "question": "Fetching available schemas..."
                    }
                elif memory.available_schemas:
                    logger.debug("Missing: result_schema (have cached list)")
                    schema_list = memory.get_schema_list_for_llm()
                    return {
                        "action": "ASK",
                        "question": f"Which schema should I write the results to?\n\nAvailable schemas:\n{schema_list}"
                    }
                else:
                    logger.debug("Missing: result_schema (no cached list)")
                    return {
                        "action": "ASK",
                        "question": "What schema should I write the results to?"
                    }
            
            if not params.get("table_name"):
                logger.debug("Missing: table_name (execute_query=true)")
                return {
                    "action": "ASK",
                    "question": "What table should I write the results to?"
                }
            # Check drop_before_create - treat empty string as missing
            drop_value = params.get("drop_before_create")
            if drop_value is None or drop_value == "":
                logger.debug("Asking about drop_before_create")
                return {
                    "action": "ASK",
                    "question": "Should I drop the table before creating it? (yes/no)"
                }
        
        # Set default for write_count if not specified (optional parameter)
        if "write_count" not in params or params.get("write_count") is None or params.get("write_count") == "":
            params["write_count"] = False
            logger.debug("Set write_count default: False")

        # If write_count is explicitly enabled, validate its sub-parameters
        if params.get("write_count") is True:
            result = ParameterValidator._check_write_count_params(params, memory, "write_count")
            if result:
                return result

        logger.debug(f"All read_sql params present: {params}")
        return None
    
    @staticmethod
    def validate_write_data_params(params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """
        Validate write_data parameters.
        
        Args:
            params: Current gathered parameters
            memory: Conversation memory
            
        Returns:
            Dict with ASK action if missing parameters, None if all valid
        """
        if not params.get("name"):
            logger.debug("Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this write_data job?"
            }
        
        if not params.get("connection"):
            logger.debug("Missing: connection for write_data")
            # Always return FETCH_CONNECTIONS to trigger dropdown UI
            # Handler will check if connections are already in memory
            return {
                "action": "FETCH_CONNECTIONS",
                "question": "Fetching available connections..."
            }
        
        if not params.get("schemas"):
            connection_name = params.get("connection")
            if connection_name and not memory.available_schemas:
                logger.debug(f"Need to fetch schemas for connection: {connection_name}")
                memory.available_schemas = []  # Clear cached schemas before fetching
                return {
                    "action": "FETCH_SCHEMAS",
                    "connection": connection_name,
                    "question": "Fetching available schemas..."
                }
            elif memory.available_schemas:
                logger.debug("Missing: schemas (have cached list)")
                schema_list = memory.get_schema_list_for_llm()
                return {
                    "action": "ASK",
                    "question": f"Which schema should I write the data to?\n\nAvailable schemas:\n{schema_list}"
                }
            else:
                logger.debug("Missing: schemas (no cached list)")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the data to?"
                }
        
        if not params.get("table"):
            logger.debug("Missing: table")
            return {
                "action": "ASK",
                "question": "What table should I write the data to?"
            }
        
        if not params.get("drop_or_truncate"):
            logger.debug("Missing: drop_or_truncate")
            return {
                "action": "ASK",
                "question": "Should I 'drop' (remove and recreate), 'truncate' (clear data), or 'none' (append)?"
            }
        
        # Set default for write_count if not specified (optional parameter)
        if "write_count" not in params or params.get("write_count") is None or params.get("write_count") == "":
            params["write_count"] = False
            logger.debug("Set write_count default: False")

        # If write_count is explicitly enabled, validate its sub-parameters
        if params.get("write_count") is True:
            result = ParameterValidator._check_write_count_params(params, memory, "write_count")
            if result:
                return result

        logger.debug(f"All write_data params present: {params}")
        return None
    
    @staticmethod
    def validate_send_email_params(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate send_email parameters.
        
        Args:
            params: Current gathered parameters
            
        Returns:
            Dict with ASK action if missing parameters, None if all valid
        """
        if not params.get("name"):
            logger.debug("Missing: name")
            return {
                "action": "ASK",
                "question": "What should I name this email job?"
            }
        
        if not params.get("to"):
            logger.debug("Missing: to")
            return {
                "action": "ASK",
                "question": "Who should I send the email to?"
            }

        # Validate 'to' email format
        to_emails = [e.strip() for e in params.get("to", "").split(',')]
        invalid_to = [e for e in to_emails if e and not ParameterValidator._is_valid_email(e)]
        if invalid_to:
            logger.debug(f"Invalid 'to' email format: {invalid_to}")
            return {
                "action": "ASK",
                "question": f"Invalid email format in 'to': {', '.join(invalid_to)}\n\nPlease provide valid email addresses (comma-separated):"
            }

        if not params.get("subject"):
            logger.debug("Missing: subject")
            return {
                "action": "ASK",
                "question": "What should the email subject be?"
            }

        # Check text - allow empty string, only ask if not provided at all
        if "text" not in params or params.get("text") is None:
            logger.debug("Missing: text")
            return {
                "action": "ASK",
                "question": "What should the email body say?"
            }

        # Set default for cc if not specified (optional parameter)
        if "cc" not in params or params.get("cc") is None:
            params["cc"] = ""
            logger.debug("Set cc default: empty string")

        # Validate 'cc' email format if provided
        if params.get("cc"):
            cc_emails = [e.strip() for e in params.get("cc", "").split(',')]
            invalid_cc = [e for e in cc_emails if e and not ParameterValidator._is_valid_email(e)]
            if invalid_cc:
                logger.debug(f"Invalid 'cc' email format: {invalid_cc}")
                return {
                    "action": "ASK",
                    "question": f"Invalid email format in 'cc': {', '.join(invalid_cc)}\n\nPlease provide valid email addresses (comma-separated), or 'none' to skip:"
                }

        logger.debug("All send_email params present and validated")
        logger.debug(f"Final params: name={params.get('name')}, to={params.get('to')}, subject={params.get('subject')[:30] if len(params.get('subject', '')) > 30 else params.get('subject')}..., cc='{params.get('cc')}'")
        return None
    
    @staticmethod
    def validate_compare_sql_params(params: Dict[str, Any], memory: Memory) -> Optional[Dict[str, Any]]:
        """
        Validate compare_sql parameters.

        Note: Key columns and mapped columns are already set from UI mapping.
        We only need to gather: schemas, table_name, job_name

        Args:
            params: Current gathered parameters
            memory: Conversation memory

        Returns:
            Dict with ASK/FETCH_SCHEMAS action if missing parameters, None if all valid
        """
        # Check if schemas is selected
        if not params.get("schemas"):
            connection_name = memory.connection
            if connection_name and not memory.available_schemas:
                logger.debug(f"Need to fetch schemas for connection: {connection_name}")
                memory.available_schemas = []
                return {
                    "action": "FETCH_SCHEMAS",
                    "connection": connection_name,
                    "question": "Fetching available schemas..."
                }
            elif memory.available_schemas:
                logger.debug("Missing: schemas (have cached list)")
                schema_list = memory.get_schema_list_for_llm()
                return {
                    "action": "ASK",
                    "question": f"Which schema should I save the comparison results to?\n\nAvailable schemas:\n{schema_list}"
                }
            else:
                logger.debug("Missing: schemas (no cached list)")
                return {
                    "action": "ASK",
                    "question": "What schema should I save the comparison results to?"
                }

        if not params.get("table_name"):
            logger.debug("Missing: table_name")
            return {
                "action": "ASK",
                "question": "What table name should I use for the comparison results?"
            }

        if not params.get("job_name"):
            logger.debug("Missing: job_name")
            return {
                "action": "ASK",
                "question": "What would you like to name this comparison job? (This helps you find it in ICC)"
            }

        # Set defaults for optional params
        if "case_sensitive" not in params:
            params["case_sensitive"] = False
        if "calculate_difference" not in params:
            params["calculate_difference"] = False
        if "drop_before_create" not in params:
            params["drop_before_create"] = True

        logger.debug(f"All compare_sql params present: {params}")
        return None
    
    @staticmethod
    def _check_write_count_params(
        params: Dict[str, Any],
        memory: Memory,
        param_prefix: str = "write_count"
    ) -> Optional[Dict[str, Any]]:
        """
        Check write_count related parameters with API-based connection/schema fetching.
        
        Args:
            params: Current gathered parameters
            memory: Conversation memory
            param_prefix: Prefix for parameter names
            
        Returns:
            Dict with ASK/FETCH_CONNECTIONS/FETCH_SCHEMAS action if missing parameters, None if all valid
        """
        # Always use singular for consistency
        schema_param = f"{param_prefix}_schema"
        
        # Step 1: Check if connection is selected
        if not params.get(f"{param_prefix}_connection"):
            # Always return FETCH_CONNECTIONS to trigger dropdown UI
            # Handler will check if connections are already in memory
            logger.debug(f"Need connection selection for {param_prefix}")
            return {
                "action": "FETCH_CONNECTIONS",
                "question": "Fetching available connections for row count..."
            }
        
        # Handle default connection selection
        if params.get(f"{param_prefix}_connection", "").strip() in ["", "same", "default"]:
            params[f"{param_prefix}_connection"] = memory.connection
            logger.debug(f"Using default connection for write_count: {memory.connection}")
        
        # Step 2: Check if schema is selected
        if not params.get(schema_param):
            connection_name = params.get(f"{param_prefix}_connection")
            # Need to fetch schemas for selected connection
            if connection_name and not memory.available_schemas:
                logger.debug(f"Need to fetch schemas for write_count connection: {connection_name}")
                memory.available_schemas = []  # Clear cached schemas before fetching
                return {
                    "action": "FETCH_SCHEMAS",
                    "connection": connection_name,
                    "question": f"Fetching available schemas from {connection_name}..."
                }
            elif memory.available_schemas:
                # Have schemas, return FETCH_SCHEMAS to trigger dropdown
                logger.debug(f"Missing: {schema_param} (have cached list)")
                return {
                    "action": "FETCH_SCHEMAS",
                    "connection": connection_name,
                    "question": "Fetching schema dropdown..."
                }
            else:
                # Fallback: ask without list
                logger.debug(f"Missing: {schema_param} (no cached list)")
                return {
                    "action": "ASK",
                    "question": "What schema should I write the row count to?"
                }
        
        # Step 3: Check if table is provided
        if not params.get(f"{param_prefix}_table"):
            logger.debug(f"Missing: {param_prefix}_table (write_count=true)")
            return {
                "action": "ASK",
                "question": "What table should I write the row count to?"
            }
        
        return None

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            bool: True if valid email format
        """
        import re
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))


class YesNoExtractor:
    """
    Extracts boolean values from yes/no user inputs.
    
    Following Single Responsibility Principle.
    """
    
    YES_VALUES = {"yes", "y", "true", "1"}
    NO_VALUES = {"no", "n", "false", "0"}
    
    @staticmethod
    def extract_boolean(user_input: str, memory: Memory, tool_name: str) -> bool:
        """
        Extract boolean from user input and update memory parameters.
        
        Args:
            user_input: User's input
            memory: Conversation memory
            tool_name: Current tool being processed
            
        Returns:
            bool: True if extraction occurred
        """
        if not user_input:
            return False
        
        user_lower = user_input.lower().strip()
        
        if user_lower not in YesNoExtractor.YES_VALUES and user_lower not in YesNoExtractor.NO_VALUES:
            return False
        
        is_yes = user_lower in YesNoExtractor.YES_VALUES
        
        if tool_name == "read_sql":
            # Match the order of questions in validate_read_sql_params
            if "execute_query" not in memory.gathered_params:
                memory.gathered_params["execute_query"] = is_yes
                logger.debug(f"Set execute_query={is_yes} from direct user input")
                return True
            # drop_before_create comes AFTER table_name is provided
            elif "drop_before_create" not in memory.gathered_params and memory.gathered_params.get("execute_query") and memory.gathered_params.get("table_name"):
                memory.gathered_params["drop_before_create"] = is_yes
                logger.debug(f"Set drop_before_create={is_yes} from direct user input")
                return True
            # write_count comes AFTER drop_before_create (or after execute_query if execute_query is False)
            elif "write_count" not in memory.gathered_params:
                memory.gathered_params["write_count"] = is_yes
                logger.debug(f"Set write_count={is_yes} from direct user input")
                return True
        elif tool_name == "write_data" and "write_count" not in memory.gathered_params:
            memory.gathered_params["write_count"] = is_yes
            logger.debug(f"Set write_count={is_yes} from direct user input")
            return True

        return False

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            bool: True if valid email format
        """
        import re
        if not email:
            return False

        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
