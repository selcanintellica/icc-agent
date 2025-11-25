from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_serializer

class WireVariable(BaseModel):
    definition: str
    id: str = ""
    value: Optional[Any] = None
    value2: Optional[Any] = Field(default=None, exclude=True)
    model_config = {"extra": "allow"}
    
    @model_serializer
    def serialize_model(self):
        """Custom serializer to include value2 only when explicitly set in a dict"""
        result = {"definition": self.definition, "id": self.id}
        if self.value is not None:
            result["value"] = self.value
        # Only include value2 if it was explicitly set (not just defaulted to None)
        if hasattr(self, '__pydantic_fields_set__') and 'value2' in self.__pydantic_fields_set__:
            result["value2"] = self.value2
        return result

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
