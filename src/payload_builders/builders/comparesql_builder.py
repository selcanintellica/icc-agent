"""
CompareSQL Wire Builder.

Handles building wire payloads for CompareSQL jobs following SOLID principles.
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel

from src.models.wire import WireVariable
from src.models.definition_map import TEMPLATES
from .base_builder import WirePayloadBuilder

logger = logging.getLogger(__name__)


class CompareSQLWireBuilder(WirePayloadBuilder):
    """
    Builder for CompareSQL wire payloads.
    
    Following SRP - only handles CompareSQL-specific logic.
    """
    
    def __init__(self):
        """Initialize CompareSQL wire builder."""
        template_meta = TEMPLATES["COMPARESQL"]
        super().__init__(
            template_id=template_meta["template_id"],
            definitions_map=template_meta["definitions"]
        )
    
    def get_template_key(self) -> str:
        """Get template key."""
        return "COMPARESQL"
    
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build CompareSQL-specific variables.
        
        CompareSQL doesn't need additional processing beyond base variables.
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Additional arguments (not used)
            
        Returns:
            List[WireVariable]: Empty list (no additional variables needed)
        """
        # CompareSQL uses only base variables
        logger.debug("CompareSQL: No additional variables needed")
        return []
