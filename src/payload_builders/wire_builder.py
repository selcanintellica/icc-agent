from typing import Any, Dict, List
from pydantic import BaseModel
from src.models.wire import WirePayload, WireVariable, WireProps
from src.models.definition_map import (
    TEMPLATES,
    DEFAULT_PRIORITY,
    DEFAULT_ACTIVE,
    DEFAULT_SKIP,
    DEFAULT_FOLDER,
    DEFAULT_RIGHTS_OWNER,
)

class UnknownTemplateKey(Exception):
    ...

def build_wire_payload(request: BaseModel, column_names = "") -> WirePayload:
    """
    Converts an object derived from BaseLLMRequest (with LLM-friendly field names)
    into a wire payload (using definition IDs).
    """
    template_key = request.template_key()
    if template_key not in TEMPLATES:
        raise UnknownTemplateKey(f"Unknown template key: {template_key}")

    meta = TEMPLATES[template_key]
    template_id: str = meta["template_id"]
    defs_map: Dict[str, str] = meta["definitions"]
    props_name: str = meta["props_name"]

    fields: Dict[str, Any] = request.to_field_values()

    variables: List[WireVariable] = []
    for field_name, value in fields.items():
        if field_name not in defs_map:
            continue
        def_id = defs_map[field_name]

        if isinstance(value, dict):
            var = WireVariable(definition=def_id, id="")
            if "value" in value:
                var.value = value["value"]
            if "value2" in value:
                var.value2 = value["value2"]
            for k, v in value.items():
                if k not in ("value", "value2"):
                    setattr(var, k, v)
            variables.append(var)
        elif isinstance(value, (list, tuple)):
            var = WireVariable(definition=def_id, id="", value=value)
            variables.append(var)
        else:

            var = WireVariable(definition=def_id, id="", value=value)
            variables.append(var)

    if template_id == "2223045341865624": # READSQL template
        formated_column_names = [
            {"columnName": name} for name in column_names
        ]
        var = WireVariable(definition=defs_map["columns"], id="", value=formated_column_names)
        variables.append(var)

    # Use job name from request.props if provided, otherwise use template default
    job_name = props_name  # Default from template
    job_active = DEFAULT_ACTIVE
    if hasattr(request, 'props') and request.props:
        job_name = request.props.get("name", props_name)
        job_active = request.props.get("active", DEFAULT_ACTIVE)
    
    wire = WirePayload(
        template=template_id,
        variables=variables,
        rights={"owner": getattr(request, "owner", DEFAULT_RIGHTS_OWNER)},
        priority=getattr(request, "priority", DEFAULT_PRIORITY),
        props=WireProps(active=job_active, name=job_name),
        skip=DEFAULT_SKIP,
        folder=getattr(request, "folder", DEFAULT_FOLDER),
    )
    return wire
