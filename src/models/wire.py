from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, PrivateAttr

class WireVariable(BaseModel):
    definition: str
    id: str = ""
    value: Optional[Any] = None
    value2: Optional[Any] = None
    _has_value2: bool = PrivateAttr(default=False)
    
    model_config = {
        "extra": "allow"
    }
    
    def __init__(self, **data):
        # Track if value2 was explicitly provided
        if 'value2' in data:
            super().__init__(**data)
            self._has_value2 = True
        else:
            super().__init__(**data)
            self._has_value2 = False
    
    def model_dump(self, **kwargs):
        """Custom dump to include value2 only when explicitly set and include extra fields"""
        from loguru import logger
        
        data = {'definition': self.definition, 'id': self.id}
        
        # Add value if it's not None
        if self.value is not None:
            data['value'] = self.value
        
        # Add value2 ONLY if it was explicitly provided in constructor (even if None)
        if self._has_value2:
            data['value2'] = self.value2
            logger.debug(f"[WireVariable] Including value2={self.value2} for definition={self.definition}")
        
        # Add any extra fields (like jobName, folder) from __pydantic_extra__
        if hasattr(self, '__pydantic_extra__') and self.__pydantic_extra__:
            logger.debug(f"[WireVariable] Found extra fields: {self.__pydantic_extra__} for definition={self.definition}")
            for field_name, value in self.__pydantic_extra__.items():
                if value is not None:
                    data[field_name] = value
                    logger.debug(f"[WireVariable] Including extra field {field_name}={value}")
        
        return data

class WireProps(BaseModel):
    active: str = "true"
    name: str

class WirePayload(BaseModel):
    template: str
    variables: List[WireVariable]
    rights: Dict[str, Any] = Field(default_factory=lambda: {"owner": ""})
    priority: str = "Normal"
    props: WireProps
    skip: str = "false"
    folder: str
    
    def model_dump(self, **kwargs):
        """Override to handle variables with custom serialization"""
        # Don't pass exclude_none to variables since we handle it custom
        data = {
            'template': self.template,
            'variables': [var.model_dump() for var in self.variables],  # Use our custom dump
            'rights': self.rights,
            'priority': self.priority,
            'props': self.props.model_dump(**kwargs),
            'skip': self.skip,
            'folder': self.folder
        }
        return data
