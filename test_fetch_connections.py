from pathlib import Path
import json

from src.utils.fetch_connections import (
    map_connection_object,
    map_connection_list_to_config,
    save_connections_to_json,
)

SAMPLE_RESPONSE = {
    "object": [
        {
            "id": "351788263695356",
            "props": {
                "active": True,
                "createdBy": "184431757886694",
                "creationDate": "2025-08-22T15:05:32.684+03:00",
                "description": "",
                "modifiedBy": "184431757886694",
                "modificationDate": "2025-09-01T03:20:31.798+03:00",
                "name": "AS400",
            },
            "databasePd": "",
            "databaseUrl": "jdbc:as400://pub400.com;prompt=false",
            "databaseUser": "OGUZHAN",
            "connectionType": "generic",
            "endpoint": "",
            "tenantId": "",
            "clientId": "",
            "clientSecret": "",
            "storageAccountName": "",
            "containerName": "",
            "rights": {
                "id": "351788263834667",
                "owner": "184431757886694",
                "roleRights": {},
                "userRights": {},
                "inheritsFromParent": True,
                "roleRightsSet": None,
                "userRightsSet": None,
            },
        },
        {
            "id": "8510874351110295",
            "props": {
                "active": True,
                "createdBy": "184431757886694",
                "creationDate": "2022-04-25T10:11:38.006+03:00",
                "description": ".,",
                "modifiedBy": "184431757886694",
                "modificationDate": "2025-08-04T01:38:56.340+03:00",
                "name": "Cassandra",
            },
            "databasePd": "",
            "databaseUrl": "jdbc:cassandra://172.16.44.17:9042;AuthMech=1",
            "databaseUser": "cassandra",
            "connectionType": "generic",
            "endpoint": "",
            "tenantId": "",
            "clientId": "",
            "clientSecret": "",
            "storageAccountName": "",
            "containerName": "",
            "rights": {
                "id": "8510874351194669",
                "owner": "184431757886694",
                "roleRights": {},
                "userRights": {},
                "inheritsFromParent": True,
                "roleRightsSet": None,
                "userRightsSet": None,
            },
        },
        {
            "id": "4305169059295890",
            "props": {
                "active": True,
                "createdBy": "184431757886694",
                "creationDate": "2021-03-22T16:27:40.932+03:00",
                "description": "",
                "modifiedBy": "184431757886694",
                "modificationDate": "2021-05-17T12:11:03.869+03:00",
                "name": "Dnext_CUSTOMER",
            },
            "databasePd": "",
            "databaseUrl": "jdbc:postgresql://172.16.44.10:5432/customer",
            "databaseUser": "postgres",
            "connectionType": "generic",
            "endpoint": None,
            "tenantId": None,
            "clientId": None,
            "clientSecret": None,
            "storageAccountName": None,
            "containerName": None,
            "rights": {
                "id": "4305169059320376",
                "owner": "184431757886694",
                "roleRights": {},
                "userRights": {},
                "inheritsFromParent": True,
                "roleRightsSet": None,
                "userRightsSet": None,
            },
        },
        {
            "id": "11114697370492838",
            "props": {
                "active": True,
                "createdBy": "184431757886694",
                "creationDate": "2024-05-24T12:04:45.738+03:00",
                "description": "",
                "modifiedBy": "184431757886694",
                "modificationDate": "2024-05-24T12:04:45.738+03:00",
                "name": "Snowflake",
            },
            "databasePd": "",
            "databaseUrl": "jdbc:snowflake://mcivjon-tm57880.snowflakecomputing.com",
            "databaseUser": "oguzhanmelez",
            "connectionType": "generic",
            "endpoint": None,
            "tenantId": None,
            "clientId": None,
            "clientSecret": None,
            "storageAccountName": None,
            "containerName": None,
            "rights": {
                "id": "11114697370581016",
                "owner": "184431757886694",
                "roleRights": {},
                "userRights": {},
                "inheritsFromParent": True,
                "roleRightsSet": None,
                "userRightsSet": None,
            },
        },
    ],
    "errorCode": None,
    "errorMessage": None,
}



def test_map_single_cassandra_connection():
    cassandra_obj = next(
        obj for obj in SAMPLE_RESPONSE["object"]
        if obj["props"]["name"] == "Cassandra"
    )

    name, mapped = map_connection_object(cassandra_obj)

    assert name == "Cassandra"
    assert mapped["id"] == "8510874351110295"
    assert mapped["url"] == "jdbc:cassandra://172.16.44.17:9042;AuthMech=1"
    assert mapped["user"] == "cassandra"
    assert mapped["db_type"] == "Cassandra"


def test_map_single_as400_connection():
    as400_obj = next(
        obj for obj in SAMPLE_RESPONSE["object"]
        if obj["props"]["name"] == "AS400"
    )

    name, mapped = map_connection_object(as400_obj)

    assert name == "AS400"
    assert mapped["id"] == "351788263695356"
    assert mapped["url"] == "jdbc:as400://pub400.com;prompt=false"
    assert mapped["user"] == "OGUZHAN"
    # infer_db_type as400 için özel case olmadığı için Generic bekliyoruz
    assert mapped["db_type"] == "Generic"


def test_map_connection_list_to_config_builds_dict_by_name():
    config = map_connection_list_to_config(SAMPLE_RESPONSE)

    # 4 connection bekliyoruz
    assert len(config) == 4

    # Key'ler connection name
    assert set(config.keys()) == {
        "AS400",
        "Cassandra",
        "Dnext_CUSTOMER",
        "Snowflake",
    }

    snow = config["Snowflake"]
    assert snow["id"] == "11114697370492838"
    assert snow["url"] == "jdbc:snowflake://mcivjon-tm57880.snowflakecomputing.com"
    assert snow["user"] == "oguzhanmelez"
    assert snow["db_type"] == "Snowflake"

        # Cassandra ve AS400 için de mapping doğru mu ek kontrol
    cass = config["Cassandra"]
    assert cass["id"] == "8510874351110295"
    assert cass["db_type"] == "Cassandra"
    assert cass["url"] == "jdbc:cassandra://172.16.44.17:9042;AuthMech=1"
    assert cass["user"] == "cassandra"

    as400 = config["AS400"]
    assert as400["id"] == "351788263695356"
    # as400 için özel case yok, Generic bekliyoruz
    assert as400["db_type"] == "Generic"
    assert as400["url"] == "jdbc:as400://pub400.com;prompt=false"
    assert as400["user"] == "OGUZHAN"

    dnext = config["Dnext_CUSTOMER"]
    assert dnext["id"] == "4305169059295890"
    assert dnext["db_type"] == "PostgreSQL"
    assert dnext["url"] == "jdbc:postgresql://172.16.44.10:5432/customer"
    assert dnext["user"] == "postgres"


def test_save_connections_to_json_creates_file():
    config = map_connection_list_to_config(SAMPLE_RESPONSE)

    root_dir = Path(__file__).resolve().parent      # icc-agent/
    data_dir = root_dir / "data"
    data_dir.mkdir(exist_ok=True)

    before_files = set(data_dir.glob("test_connections_*.json"))

    save_connections_to_json(config, "test_connections.json")

    after_files = set(data_dir.glob("test_connections_*.json"))
    new_files = after_files - before_files

    assert len(new_files) == 1

    created_file = new_files.pop()
    assert created_file.exists()

    with created_file.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded.keys() == config.keys()
    assert loaded["Cassandra"]["id"] == config["Cassandra"]["id"]