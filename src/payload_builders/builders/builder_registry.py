"""
Builder Registry for Wire Payload Builders.

Centralized registry mapping template keys to builder instances.
Follows Open-Closed Principle - open for extension via registration.
"""

import logging
from typing import Dict, Optional

from .base_builder import WirePayloadBuilder
from .readsql_builder import ReadSQLWireBuilder
from .writedata_builder import WriteDataWireBuilder
from .sendemail_builder import SendEmailWireBuilder
from .comparesql_builder import CompareSQLWireBuilder

logger = logging.getLogger(__name__)


class BuilderRegistry:
    """
    Registry for wire payload builders.
    
    Follows OCP - register new builders without modifying existing code.
    Follows SRP - only manages builder registration and retrieval.
    """
    
    def __init__(self):
        """Initialize builder registry with default builders."""
        self._builders: Dict[str, WirePayloadBuilder] = {}
        self._register_default_builders()
    
    def _register_default_builders(self) -> None:
        """Register all default wire builders."""
        self.register("READSQL", ReadSQLWireBuilder())
        self.register("WRITEDATA", WriteDataWireBuilder())
        self.register("SENDEMAIL", SendEmailWireBuilder())
        self.register("COMPARESQL", CompareSQLWireBuilder())
        logger.info("Registered 4 default wire builders")
    
    def register(self, template_key: str, builder: WirePayloadBuilder) -> None:
        """
        Register a builder for a template key.
        
        Args:
            template_key: Template key (e.g., "READSQL")
            builder: Builder instance
        """
        if template_key in self._builders:
            logger.warning(f"Overwriting existing builder for {template_key}")
        
        self._builders[template_key] = builder
        logger.debug(f"Registered builder for template: {template_key}")
    
    def get_builder(self, template_key: str) -> Optional[WirePayloadBuilder]:
        """
        Get builder for a template key.
        
        Args:
            template_key: Template key (e.g., "READSQL")
            
        Returns:
            WirePayloadBuilder instance or None if not found
        """
        builder = self._builders.get(template_key)
        
        if builder is None:
            logger.error(f"No builder registered for template: {template_key}")
        else:
            logger.debug(f"Retrieved builder for template: {template_key}")
        
        return builder
    
    def has_builder(self, template_key: str) -> bool:
        """
        Check if builder exists for template key.
        
        Args:
            template_key: Template key to check
            
        Returns:
            bool: True if builder exists
        """
        return template_key in self._builders
    
    def list_templates(self) -> list[str]:
        """
        List all registered template keys.
        
        Returns:
            list[str]: List of template keys
        """
        return list(self._builders.keys())


# Global registry instance (singleton pattern)
_registry: Optional[BuilderRegistry] = None


def get_builder_registry() -> BuilderRegistry:
    """
    Get global builder registry instance.
    
    Implements singleton pattern - one registry per application.
    
    Returns:
        BuilderRegistry: Global registry instance
    """
    global _registry
    
    if _registry is None:
        _registry = BuilderRegistry()
        logger.info("Created global BuilderRegistry instance")
    
    return _registry
