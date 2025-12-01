"""
SendEmail Wire Builder.

Handles building wire payloads for SendEmail jobs following SOLID principles.
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel

from src.models.wire import WireVariable
from src.models.definition_map import TEMPLATES
from .base_builder import WirePayloadBuilder

logger = logging.getLogger(__name__)


class SendEmailWireBuilder(WirePayloadBuilder):
    """
    Builder for SendEmail wire payloads.
    
    Following SRP - only handles SendEmail-specific logic.
    """
    
    def __init__(self):
        """Initialize SendEmail wire builder."""
        template_meta = TEMPLATES["SENDEMAIL"]
        super().__init__(
            template_id=template_meta["template_id"],
            definitions_map=template_meta["definitions"]
        )
    
    def get_template_key(self) -> str:
        """Get template key."""
        return "SENDEMAIL"
    
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build SendEmail-specific variables.
        
        SendEmail doesn't need additional processing beyond base variables.
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Additional arguments (not used)
            
        Returns:
            List[WireVariable]: Empty list (no additional variables needed)
        """
        # SendEmail uses only base variables
        logger.debug("SendEmail: No additional variables needed")
        return []
