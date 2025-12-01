"""
Refactored Wire Builder using Builder Registry and Dependency Injection.

Main entry point for building wire payloads - delegates to template-specific builders.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from src.models.wire import WirePayload
from .builders import get_builder_registry, BuilderRegistry

logger = logging.getLogger(__name__)


class UnknownTemplateKey(Exception):
    """Exception raised when template key is not found in registry."""
    pass


class WireBuilder:
    """
    Wire builder that delegates to template-specific builders.
    
    Follows OCP - open for extension by registering new builders.
    Follows DIP - depends on BuilderRegistry abstraction.
    """
    
    def __init__(self, registry: Optional[BuilderRegistry] = None):
        """
        Initialize wire builder.
        
        Args:
            registry: Builder registry (uses global if not provided)
        """
        self._registry = registry or get_builder_registry()
    
    def build_wire_payload(
        self,
        request: BaseModel,
        column_names: str = ""
    ) -> WirePayload:
        """
        Build wire payload for a request.
        
        Delegates to appropriate template-specific builder.
        
        Args:
            request: Request model with template_key() and to_field_values()
            column_names: Optional column names (for backward compatibility)
            
        Returns:
            WirePayload: Built wire payload
            
        Raises:
            UnknownTemplateKey: If no builder for template key
        """
        template_key = request.template_key()
        logger.info(f"Building wire payload for template: {template_key}")
        
        # Get builder for template
        builder = self._registry.get_builder(template_key)
        if builder is None:
            available = self._registry.list_templates()
            raise UnknownTemplateKey(
                f"Unknown template key: {template_key}. "
                f"Available templates: {', '.join(available)}"
            )
        
        # Delegate to builder
        wire = builder.build(request, column_names=column_names)
        
        logger.info(
            f"Built wire payload: template={wire.template}, "
            f"variables={len(wire.variables)}, "
            f"job_name={wire.props.name}"
        )
        
        return wire


# Global builder instance (singleton pattern)
_builder: Optional[WireBuilder] = None


def get_wire_builder() -> WireBuilder:
    """
    Get global wire builder instance.
    
    Returns:
        WireBuilder: Global builder instance
    """
    global _builder
    
    if _builder is None:
        _builder = WireBuilder()
        logger.info("Created global WireBuilder instance")
    
    return _builder


def build_wire_payload(request: BaseModel, column_names: str = "") -> WirePayload:
    """
    Build wire payload for a request (backward compatibility function).
    
    Args:
        request: Request model
        column_names: Optional column names
        
    Returns:
        WirePayload: Built wire payload
    """
    return get_wire_builder().build_wire_payload(request, column_names)
