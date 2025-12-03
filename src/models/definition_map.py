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
            "write_count_schema": "28405919737373",
            "write_count_table": "28405919059373",
            "execute_query": "28405919526172",
            "result_schema": "284961720523",
            "table_name": "284961720524",
            "drop_before_create": "284961720525",
            "only_dataset_columns": "284961720526",
            "columns": "2223045341958051",
        },
        "props_name": "readsql10",
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
            "report_format": "28405919087238",
            "only_dataset_columns": "28405919100737",
            "write_count": "28405919839465",
            "write_count_connection": "28405919193743",
            "write_count_schemas": "28405919284178",
            "write_count_table": "28405919372169",
        },
        "props_name": "writedata",
    },
    "COMPARESQL": {
        "template_id": "1236441135395",
        "definitions": {
            "connection": "729110340002981",
            "first_sql_query": "530459168004987",
            "second_sql_query": "530459168003985",
            "first_table_keys": "530459168112986",
            "second_table_keys": "530412368194984",
            "map_table": "729110340002977",
            "keys": "729110340002978",
            "case_sensitive": "1614692916",
            "save_result_in_cache": "729110349001983",
            "reporting": "729110340002982",
            "drop_before_create": "729110349001984",
            "schemas": "729110340002980",
            "table_name": "729110340002979",
            "columns_output": "530451118194737",
        },
        "props_name": "comparesql",
    },
}


DEFAULT_PRIORITY = "Normal"
DEFAULT_ACTIVE = "true"
DEFAULT_SKIP = "false"
DEFAULT_FOLDER = "3023602439587835"
DEFAULT_RIGHTS_OWNER = "184431757886694"
