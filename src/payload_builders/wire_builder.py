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
    from loguru import logger
    
    template_key = request.template_key()
    if template_key not in TEMPLATES:
        raise UnknownTemplateKey(f"Unknown template key: {template_key}")

    meta = TEMPLATES[template_key]
    template_id: str = meta["template_id"]
    defs_map: Dict[str, str] = meta["definitions"]
    props_name: str = meta["props_name"]

    fields: Dict[str, Any] = request.to_field_values()
    logger.info(f"[WireBuilder] Template: {template_key}, Fields from to_field_values(): {fields}")

    variables: List[WireVariable] = []
    for field_name, value in fields.items():
        if field_name not in defs_map:
            continue
        def_id = defs_map[field_name]

        if isinstance(value, dict):
            # When value is a dict, pass all fields to constructor to ensure proper tracking
            var_dict = {"definition": def_id, "id": ""}
            if "value" in value:
                var_dict["value"] = value["value"]
            if "value2" in value:
                var_dict["value2"] = value["value2"]
            # Add any other custom fields
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

    if template_id == "2223045341865624": # READSQL template
        formated_column_names = [
            {"columnName": name} for name in column_names
        ]
        var = WireVariable(definition=defs_map["columns"], id="", value=formated_column_names)
        variables.append(var)

    wire = WirePayload(
        template=template_id,
        variables=variables,
        rights={"owner": getattr(request, "owner", DEFAULT_RIGHTS_OWNER)},
        priority=getattr(request, "priority", DEFAULT_PRIORITY),
        props=WireProps(active=DEFAULT_ACTIVE, name=props_name),
        skip=DEFAULT_SKIP,
        folder=getattr(request, "folder", DEFAULT_FOLDER),
    )
    
    logger.info(f"[WireBuilder] Built WirePayload with {len(variables)} variables")
    for var in variables:
        logger.info(f"[WireBuilder] Variable: definition={var.definition}, id={var.id}, value={getattr(var, 'value', 'N/A')}, value2={getattr(var, 'value2', 'N/A')}")
    
    return wire
