"""
WriteData Wire Builder.

Handles building wire payloads for WriteData jobs following SOLID principles.
"""

import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel

from src.models.wire import WireVariable
from src.models.definition_map import TEMPLATES, DEFAULT_FOLDER
from .base_builder import WirePayloadBuilder

logger = logging.getLogger(__name__)


class WriteDataWireBuilder(WirePayloadBuilder):
    """
    Builder for WriteData wire payloads.
    
    Following SRP - only handles WriteData-specific logic.
    """
    
    def __init__(self):
        """Initialize WriteData wire builder."""
        template_meta = TEMPLATES["WRITEDATA"]
        super().__init__(
            template_id=template_meta["template_id"],
            definitions_map=template_meta["definitions"]
        )
    
    def get_template_key(self) -> str:
        """Get template key."""
        return "WRITEDATA"
    
    def get_excluded_fields(self) -> List[str]:
        """Exclude fields from base processing since we handle them specially."""
        return ["columns", "add_columns", "data_set"]
    
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build WriteData-specific variables.
        
        Handles:
        1. data_set with jobName and folder metadata
        2. columns conversion to JSON
        3. add_columns as empty string
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Additional arguments (not used)
            
        Returns:
            List[WireVariable]: WriteData-specific variables
        """
        variables = []
        
        # Get metadata from request
        data_set_job_name = None
        data_set_folder = None
        if hasattr(request, 'variables') and len(request.variables) > 0:
            var = request.variables[0]
            data_set_job_name = getattr(var, 'data_set_job_name', None)
            data_set_folder = getattr(var, 'data_set_folder', None)
        
        # 1. Update data_set variable with metadata
        if "data_set" in fields:
            job_id = fields["data_set"]
            variables.append(
                WireVariable(
                    definition=self.definitions_map["data_set"],
                    id="",
                    value=job_id,
                    jobName=data_set_job_name or "readsql",
                    folder=data_set_folder or DEFAULT_FOLDER
                )
            )
            logger.info(f"Added data_set: job_id={job_id}, jobName={data_set_job_name}, folder={data_set_folder}")
        
        # 2. Convert columns to JSON string
        if "columns" in fields:
            columns_value = fields["columns"]
            if isinstance(columns_value, list):
                columns_dict = []
                for col in columns_value:
                    if hasattr(col, 'model_dump'):
                        columns_dict.append(col.model_dump())
                    elif hasattr(col, 'dict'):
                        columns_dict.append(col.dict())
                    elif isinstance(col, dict):
                        columns_dict.append(col)
                
                columns_json = json.dumps(columns_dict)
                variables.append(
                    WireVariable(
                        definition=self.definitions_map["columns"],
                        id="",
                        value=columns_json
                    )
                )
                logger.info(f"Converted {len(columns_dict)} columns to JSON")
        
        # 3. Ensure add_columns is empty string
        variables.append(
            WireVariable(
                definition=self.definitions_map["add_columns"],
                id="",
                value=""
            )
        )
        logger.debug("Set add_columns to empty string")
        
        return variables
