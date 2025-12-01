"""
ReadSQL Wire Builder.

Handles building wire payloads for ReadSQL jobs following SOLID principles.
"""

import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel

from src.models.wire import WireVariable
from src.models.definition_map import TEMPLATES
from .base_builder import WirePayloadBuilder

logger = logging.getLogger(__name__)


class ReadSQLWireBuilder(WirePayloadBuilder):
    """
    Builder for ReadSQL wire payloads.
    
    Following SRP - only handles ReadSQL-specific logic.
    """
    
    def __init__(self):
        """Initialize ReadSQL wire builder."""
        template_meta = TEMPLATES["READSQL"]
        super().__init__(
            template_id=template_meta["template_id"],
            definitions_map=template_meta["definitions"]
        )
    
    def get_template_key(self) -> str:
        """Get template key."""
        return "READSQL"
    
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build ReadSQL-specific variables (columns).
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Must contain 'column_names' list
            
        Returns:
            List[WireVariable]: ReadSQL-specific variables
        """
        column_names = kwargs.get('column_names', [])
        
        if not column_names:
            logger.warning("No column names provided for ReadSQL wire payload")
            return []
        
        # Format columns as required by API
        formatted_columns = [{"columnName": name} for name in column_names]
        
        # Convert to JSON string
        columns_json = json.dumps(formatted_columns)
        
        logger.info(f"Added {len(column_names)} columns to ReadSQL wire payload")
        
        return [
            WireVariable(
                definition=self.definitions_map["columns"],
                id="",
                value=columns_json
            )
        ]
