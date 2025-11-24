"""
Connection configuration mapping connection names to their IDs and metadata.
Used for API calls that require connection IDs.
"""
from typing import Dict, Any, Optional

CONNECTIONS: Dict[str, Dict[str, Any]] = {
    "Cassandra": {
        "id": "5861393593217446",
        "db_type": "Cassandra",
        "url": "jdbc:cassandra://172.16.44.17:9042;AuthMech=1",
        "user": "cassandra",
    },
    "HANA": {
        "id": "8448800292564427",
        "db_type": "SAP HANA",
        "url": "jdbc:sap://172.16.44.15:39015",
        "user": "SYSTEM",
    },
    "Hive": {
        "id": "8453303386327603",
        "db_type": "Hive",
        "url": "jdbc:hive2://172.16.44.17:10000/default",
        "user": "hive",
    },
    "MSSQL": {
        "id": "8449030761986558",
        "db_type": "SQL Server",
        "url": "jdbc:sqlserver://172.16.44.11:1433;databaseName=master",
        "user": "sa",
    },
    "Mongo": {
        "id": "2929902649070900",
        "db_type": "MongoDB",
        "url": "mongodb://172.16.44.11:27017/testdb",
        "user": "testuser",
    },
    "NETEZZA": {
        "id": "1829742320324078",
        "db_type": "Netezza",
        "url": "jdbc:netezza://172.16.44.13:5480/SYSTEM",
        "user": "admin",
    },
    "ORACLE_10": {
        "id": "955448816772621",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
        "user": "icc_test",
    },
    "ORACLE_11": {
        "id": "9592123237737",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@172.16.44.11:1521:ORCL19C",
        "user": "ICC_META",
    },
    "oracle_18": {
        "id": "23061586410134803",
        "db_type": "Oracle",
        "url": "jdbc:oracle:thin:@172.16.44.18:1521:ORCL19C",
        "user": "ICC_DEV_META",
    },
    "POSTGRE_11": {
        "id": "955225233921727",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.11:5432/postgres",
        "user": "postgres",
    },
    "POSTGRE_14": {
        "id": "2433676967192755",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.14:5432/postgres",
        "user": "icc_test",
    },
    "POSTGRE_DEMO": {
        "id": "3134782933199896",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.21:5432/postgres",
        "user": "postgres",
    },
    "Postgresql": {
        "id": "8449161086856529",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.11:5432/postgres",
        "user": "icc",
    },
    "VFPT_POSTGRESQL": {
        "id": "31817712937260880",
        "db_type": "PostgreSQL",
        "url": "jdbc:postgresql://172.16.44.21:5432/postgres",
        "user": "postgres",
    },
    "SFTP_SERVER": {
        "id": "32050305818626884",
        "db_type": "SFTP",
        "url": "ftp://172.16.22.10:22",
        "user": "sftpuser",
    },
    "ozlem_908": {
        "id": "13926603303722332",
        "db_type": "Azure Data Lake",
        "url": None,
        "user": None,
    },
    "piateam_azure_data_lake": {
        "id": "13924989252846968",
        "db_type": "Azure Data Lake",
        "url": "https://storagepiateam.blob.core.windows.net",
        "user": "icc-no-reply@intellica.net",
    },
}


def get_connection_id(connection_name: str) -> Optional[str]:
    """
    Get connection ID for a given connection name.
    
    Args:
        connection_name: Name of the connection (e.g., "ORACLE_10")
        
    Returns:
        Connection ID string or None if not found
    """
    conn = CONNECTIONS.get(connection_name)
    if conn:
        return conn["id"]
    return None


def get_connection_info(connection_name: str) -> Optional[Dict[str, Any]]:
    """
    Get full connection information for a given connection name.
    
    Args:
        connection_name: Name of the connection
        
    Returns:
        Dictionary with connection info or None if not found
    """
    return CONNECTIONS.get(connection_name)


def list_connections() -> Dict[str, Dict[str, Any]]:
    """
    Get all available connections.
    
    Returns:
        Dictionary of all connections
    """
    return CONNECTIONS
