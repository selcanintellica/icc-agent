"""
Base Wire Payload Builder.

Defines the interface for all wire payload builders following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel
import logging

from src.models.wire import WirePayload, WireVariable, WireProps
from src.models.definition_map import (
    DEFAULT_PRIORITY,
    DEFAULT_ACTIVE,
    DEFAULT_SKIP,
    DEFAULT_FOLDER,
    DEFAULT_RIGHTS_OWNER,
)

logger = logging.getLogger(__name__)


class WirePayloadBuilder(ABC):
    """
    Abstract base class for wire payload builders.
    
    Following SOLID principles:
    - Single Responsibility: Each builder handles one template type
    - Open/Closed: Easy to add new builders without modifying existing code
    - Liskov Substitution: All builders can be used interchangeably
    - Interface Segregation: Single focused interface
    - Dependency Inversion: Depends on abstractions
    """
    
    def __init__(self, template_id: str, definitions_map: Dict[str, str]):
        """
        Initialize wire payload builder.
        
        Args:
            template_id: Template ID for this builder
            definitions_map: Map of field names to definition IDs
        """
        self.template_id = template_id
        self.definitions_map = definitions_map
    
    @abstractmethod
    def get_template_key(self) -> str:
        """
        Get the template key identifier.
        
        Returns:
            str: Template key (e.g., "READSQL", "WRITEDATA")
        """
        pass
    
    def build(self, request: BaseModel, **kwargs) -> WirePayload:
        """
        Build wire payload from request.
        
        Args:
            request: Request model with LLM-friendly field names
            **kwargs: Additional builder-specific arguments
            
        Returns:
            WirePayload: Built wire payload
        """
        logger.info(f"Building {self.get_template_key()} wire payload")
        
        # Get field values from request
        fields = request.to_field_values()
        
        # Get props name
        props_name = self._get_props_name(request)
        
        # Get excluded fields (fields handled in template-specific builder)
        excluded_fields = self.get_excluded_fields()
        
        # Build base variables
        variables = self._build_base_variables(fields, excluded_fields)
        
        # Add template-specific variables
        additional_vars = self.build_template_specific_variables(request, fields, **kwargs)
        variables.extend(additional_vars)
        
        # Get job name and active status
        job_name, job_active = self._get_job_props(request, props_name)
        
        # Build final payload
        wire = WirePayload(
            template=self.template_id,
            variables=variables,
            rights={"owner": getattr(request, "owner", DEFAULT_RIGHTS_OWNER)},
            priority=getattr(request, "priority", DEFAULT_PRIORITY),
            props=WireProps(active=job_active, name=job_name),
            skip=DEFAULT_SKIP,
            folder=getattr(request, "folder", DEFAULT_FOLDER),
        )
        
        self._log_payload_info(wire)
        return wire
    
    def get_excluded_fields(self) -> List[str]:
        """
        Get list of field names that should be excluded from base variable processing.
        These fields will be handled in build_template_specific_variables instead.
        
        Returns:
            List[str]: Field names to exclude
        """
        return []
    
    @abstractmethod
    def build_template_specific_variables(
        self,
        request: BaseModel,
        fields: Dict[str, Any],
        **kwargs
    ) -> List[WireVariable]:
        """
        Build template-specific variables.
        
        Args:
            request: Original request model
            fields: Field values from request
            **kwargs: Additional arguments
            
        Returns:
            List[WireVariable]: Template-specific variables
        """
        pass
    
    def _build_base_variables(self, fields: Dict[str, Any], excluded_fields: List[str] = None) -> List[WireVariable]:
        """
        Build base variables from fields.
        
        Args:
            fields: Field values dictionary
            excluded_fields: List of field names to exclude from base processing
            
        Returns:
            List[WireVariable]: Base variables
        """
        if excluded_fields is None:
            excluded_fields = []
        
        variables = []
        
        for field_name, value in fields.items():
            if field_name not in self.definitions_map or field_name in excluded_fields:
                continue
            
            def_id = self.definitions_map[field_name]
            
            if isinstance(value, dict):
                # Handle dict values with proper tracking
                var_dict = {"definition": def_id, "id": ""}
                if "value" in value:
                    var_dict["value"] = value["value"]
                if "value2" in value:
                    var_dict["value2"] = value["value2"]
                # Add custom fields
                for k, v in value.items():
                    if k not in ("value", "value2", "definition", "id"):
                        var_dict[k] = v
                var = WireVariable(**var_dict)
                variables.append(var)
            elif isinstance(value, (list, tuple)):
                var = WireVariable(definition=def_id, id="", value=value)
                variables.append(var)
            else:
                var = WireVariable(definition=def_id, id="", value=value)
                variables.append(var)
        
        return variables
    
    def _get_props_name(self, request: BaseModel) -> str:
        """Get props name from request or default."""
        if hasattr(request, 'props') and isinstance(request.props, dict):
            return request.props.get('name', self.get_template_key())
        return self.get_template_key()
    
    def _get_job_props(self, request: BaseModel, default_name: str) -> tuple[str, str]:
        """Get job name and active status."""
        job_name = default_name
        job_active = DEFAULT_ACTIVE
        
        if hasattr(request, 'props') and request.props:
            job_name = request.props.get("name", default_name)
            job_active = request.props.get("active", DEFAULT_ACTIVE)
        
        return job_name, job_active
    
    def _log_payload_info(self, wire: WirePayload) -> None:
        """Log payload information."""
        logger.info(f"Built {self.get_template_key()} WirePayload with {len(wire.variables)} variables")
        for var in wire.variables:
            extra_fields = {}
            for field in ['jobName', 'folder']:
                if hasattr(var, field):
                    extra_fields[field] = getattr(var, field)
            value_str = str(getattr(var, 'value', 'N/A'))[:50] if hasattr(var, 'value') else 'N/A'
            logger.debug(f"Variable: def={var.definition}, value={value_str}, extra={extra_fields}")
