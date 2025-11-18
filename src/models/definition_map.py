from typing import Dict, Any

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "SENDEMAIL": {
        "template_id": "110673709194435",
        "definitions": {

            "connection": "110673709476681",
            "query": "110673709444744",
            "to": "110673709461441",
            "cc": "110673709490605",
            "subject": "110673709380478",
            "text": "110673709424784",
            "attachment": "1600766934",
        },
        "props_name": "SENDEMAIL",
    },
    "READSQL": {
        "template_id": "2223045341865624",
        "definitions": {
            "connection": "2223045341969932",
            "query": "2223045341935949",
            "write_count": "28405919373737",
            "write_count_connection": "28405919100373",
            "write_count_table": "28405919059373",
            "execute_query": "28405919526172",
            "result_schema": "284961720523",
            "table_name": "284961720524",
            "drop_before_create": "284961720525",
            "only_dataset_columns": "284961720526",
            "columns": "2223045341958051",
        },
        "props_name": "readsql",
    },
    "WRITEDATA": {
        "template_id": "28405918884279",
        "definitions": {
            "data_set": "28405919074002",
            "columns": "28405919027068",
            "add_columns": "28405918976213",
            "connection": "28405919100547",
            "schemas": "28405919042037",
            "table": "28405919059935",
            "drop_or_truncate": "28405919008625",
            "only_dataset_columns": "28405919100737",
            "write_count": "28405919839465",
            "write_count_connection": "28405919193743",
            "write_count_schemas": "28405919284178",
            "write_count_table": "28405919372169",
        },
        "props_name": "writedata",
    },
}


DEFAULT_PRIORITY = "Normal"
DEFAULT_ACTIVE = "true"
DEFAULT_SKIP = "false"
DEFAULT_FOLDER = "3023602439587835"
DEFAULT_RIGHTS_OWNER = "184431757886694"
