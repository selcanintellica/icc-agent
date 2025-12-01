"""
CompareSQL Column Output Generator.

Handles generation of columns_output structure for CompareSQL jobs.
Follows Single Responsibility Principle.
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CompareSQLColumnGenerator:
    """
    Generates columns_output structure for CompareSQL jobs.
    
    Following SOLID principles:
    - Single Responsibility: Only generates column output structure
    - Open-Closed: Easy to extend with new column types
    """
    
    @staticmethod
    def generate_columns_output(
        first_table_keys: str,
        second_table_keys: str
    ) -> str:
        """
        Generate columns_output JSON string for CompareSQL job.
        
        Args:
            first_table_keys: Comma-separated keys for first table
            second_table_keys: Comma-separated keys for second table
            
        Returns:
            str: JSON string with column definitions
        """
        logger.debug("Generating columns_output for CompareSQL")
        
        output_cols: List[Dict[str, Any]] = []
        
        # Add initial columns
        output_cols.extend([
            {"columnName": "FIRST_SQL_QUERY"},
            {"columnName": "FIRST_TABLE_KEYS"}
        ])
        
        # Add columns for first table keys
        first_keys_list = [k.strip() for k in first_table_keys.split(",") if k.strip()]
        for i, _ in enumerate(first_keys_list, 1):
            output_cols.append({"columnName": f"FIRST_KEY_{i}"})
        
        logger.debug(f"Added {len(first_keys_list)} first table key columns")
        
        # Add middle section columns
        output_cols.extend([
            {"columnName": "FIRST_COLUMN"},
            {"columnName": "FIRST_VALUE"},
            {"columnName": "FIRST_TABLE_COUNT"},
            {"columnName": "SECOND_SQL_QUERY"},
            {"columnName": "SECOND_TABLE_KEYS"}
        ])
        
        # Add columns for second table keys
        second_keys_list = [k.strip() for k in second_table_keys.split(",") if k.strip()]
        for i, _ in enumerate(second_keys_list, 1):
            output_cols.append({"columnName": f"SECOND_KEY_{i}"})
        
        logger.debug(f"Added {len(second_keys_list)} second table key columns")
        
        # Add final columns
        output_cols.extend([
            {"columnName": "SECOND_COLUMN"},
            {"columnName": "SECOND_VALUE"},
            {"columnName": "SECOND_TABLE_COUNT"}
        ])
        
        columns_json = json.dumps(output_cols)
        logger.info(f"Generated columns_output with {len(output_cols)} columns")
        
        return columns_json
    
    @staticmethod
    def parse_key_columns(keys_string: str) -> List[str]:
        """
        Parse comma-separated keys string into list.
        
        Args:
            keys_string: Comma-separated keys
            
        Returns:
            List[str]: List of trimmed key names
        """
        return [k.strip() for k in keys_string.split(",") if k.strip()]
