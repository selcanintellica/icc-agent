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

    fields: Dict[str, Any] = request.to_field_values()
    logger.info(f"[WireBuilder] Template: {template_key}, Fields from to_field_values(): {fields}")
    
    # Get props name from request.props if it exists, otherwise use default from template
    if hasattr(request, 'props') and isinstance(request.props, dict) and 'name' in request.props:
        props_name: str = request.props['name']
    else:
        props_name: str = meta["props_name"]

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
            logger.info(f"[WireBuilder] Created variable with dict, fields_set: {var.__pydantic_fields_set__ if hasattr(var, '__pydantic_fields_set__') else 'N/A'}, var_dict: {var_dict}")
            variables.append(var)
        elif isinstance(value, (list, tuple)):
            var = WireVariable(definition=def_id, id="", value=value)
            variables.append(var)
        else:

            var = WireVariable(definition=def_id, id="", value=value)
            variables.append(var)

    if template_id == "2223045341865624": # READSQL template
        import json
        formated_column_names = [
            {"columnName": name} for name in column_names
        ]
        # Convert to JSON string to match API expectation
        columns_json_string = json.dumps(formated_column_names)
        var = WireVariable(definition=defs_map["columns"], id="", value=columns_json_string)
        variables.append(var)
    
    elif template_id == "28405918884279": # WRITEDATA template
        import json
        
        # Get data_set metadata from the request variables
        data_set_job_name = None
        data_set_folder = None
        if hasattr(request, 'variables') and len(request.variables) > 0:
            var = request.variables[0]
            data_set_job_name = getattr(var, 'data_set_job_name', None)
            data_set_folder = getattr(var, 'data_set_folder', None)
        
        # 1. Update data_set variable to add jobName and folder from ReadSQL job
        for i, var in enumerate(variables):
            if var.definition == defs_map.get("data_set"):
                job_id = getattr(var, 'value', '')
                variables[i] = WireVariable(
                    definition=var.definition,
                    id=var.id,
                    value=job_id,
                    jobName=data_set_job_name or "readsql",
                    folder=data_set_folder or DEFAULT_FOLDER
                )
                logger.info(f"[WireBuilder] Updated data_set: value={job_id}, jobName={data_set_job_name}, folder={data_set_folder}")
                break
        
        # 2. Convert columns to JSON string (same as ReadSQL format)
        for i, var in enumerate(variables):
            if var.definition == defs_map.get("columns"):
                columns_value = getattr(var, 'value', [])
                if isinstance(columns_value, list):
                    columns_dict = []
                    for col in columns_value:
                        if hasattr(col, 'model_dump'):
                            columns_dict.append(col.model_dump())
                        elif hasattr(col, 'dict'):
                            columns_dict.append(col.dict())
                        elif isinstance(col, dict):
                            columns_dict.append(col)
                    columns_json_string = json.dumps(columns_dict)
                    variables[i] = WireVariable(definition=var.definition, id=var.id, value=columns_json_string)
                    logger.info(f"[WireBuilder] Converted columns to JSON: {columns_json_string[:100]}...")
                break
        
        # 3. Ensure add_columns is empty string (not empty list)
        for i, var in enumerate(variables):
            if var.definition == defs_map.get("add_columns"):
                variables[i] = WireVariable(definition=var.definition, id="", value="")
                logger.info(f"[WireBuilder] Set add_columns to empty string")
                break

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
    
    logger.info(f"[WireBuilder] Built WirePayload with {len(variables)} variables")
    for var in variables:
        # Check for extra fields
        extra_fields = {}
        for field in ['jobName', 'folder']:
            if hasattr(var, field):
                extra_fields[field] = getattr(var, field)
        logger.info(f"[WireBuilder] Variable: definition={var.definition}, id={var.id}, value={getattr(var, 'value', 'N/A')[:50] if isinstance(getattr(var, 'value', 'N/A'), str) else getattr(var, 'value', 'N/A')}, extra_fields={extra_fields}")
    
    return wire
