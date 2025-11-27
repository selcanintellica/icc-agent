from __future__ import annotations

from pathlib import Path
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from src.utils.auth import authenticate

logger = logging.getLogger(__name__)


async def fetch_connection_list(base_url: Optional[str] = None, auth_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    ICC connection list endpoint'ine GET isteği atar ve JSON döner.
    Uses the same authentication pattern as other repositories.
    
    Args:
        base_url: API endpoint URL (if None, uses ICC_CONNECTION_LIST_URL env var)
        auth_headers: Optional dict with Authorization and TokenKey headers
        
    Returns:
        JSON response from the API
    """
    if base_url is None:
        base_url = os.getenv("ICC_CONNECTION_LIST_URL")
    
    if not base_url:
        raise RuntimeError("ICC_CONNECTION_LIST_URL env variable is not set and no base_url provided")

    logger.info(f"🔌 Fetching connection list from: {base_url}")
    logger.info(f"🔐 Auth: {'enabled' if auth_headers else 'disabled'}")
    
    try:
        async with httpx.AsyncClient(headers=auth_headers or {}, verify=False, timeout=30.0) as client:
            resp = await client.get(base_url)
            
            logger.info(f"📡 Response status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            
            objects = data.get('object', [])
            logger.info(f"✅ Successfully fetched {len(objects)} connections from API")
            
            if len(objects) == 0:
                logger.warning("⚠️ API returned empty connection list! Check API response format.")
                logger.warning(f"📄 Raw response keys: {list(data.keys())}")
            
            return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching connection list: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error fetching connection list: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        raise


def infer_db_type(name: str, database_url: Optional[str], connection_type: str) -> str:
    """
    Verilen isim, database_url ve connection_type bilgilerine göre
    bağlantının DB tipini tahmin eder.
    """
    url = (database_url or "").lower()
    name_lower = name.lower()
    ctype = (connection_type or "").lower()

    if "jdbc:postgresql" in url or "postgre" in name_lower:
        return "PostgreSQL"
    if "jdbc:oracle" in url or "oracle" in name_lower:
        return "Oracle"
    if "jdbc:sqlserver" in url or "mssql" in name_lower or "sql server" in name_lower:
        return "SQL Server"
    if "jdbc:hive2" in url or "hive" in name_lower:
        return "Hive"
    if "jdbc:sap" in url or "hana" in name_lower:
        return "SAP HANA"
    if url.startswith("mongodb") or "mongo" in name_lower:
        return "MongoDB"
    if url.startswith("jdbc:cassandra") or "cassandra" in name_lower:
        return "Cassandra"
    if "snowflakecomputing.com" in url or "snowflake" in name_lower:
        return "Snowflake"
    if ctype == "oauth2":
        return "Azure Data Lake"
    if url.startswith("ftp://") or "sftp" in name_lower:
        return "SFTP"

    # Fallback
    return "Generic"


def map_connection_object(obj: Dict[str, Any]) -> Optional[tuple[str, Dict[str, Any]]]:
    """
    Tek bir connection nesnesini (response içindeki object elemanlarından biri)
    iç formatımıza (connections.py'ye benzer) dönüştürür.

    returns:
        (name, { "id": ..., "db_type": ..., "url": ..., "user": ... })
    """
    conn_id = obj.get("id")
    props = obj.get("props") or {}
    name = props.get("name")

    if not name or not conn_id:
        # İsim veya id yoksa bu kaydı atlıyoruz
        logger.debug(f"Skipping connection with missing name or id: {obj}")
        return None

    database_url = obj.get("databaseUrl") or ""
    database_user = obj.get("databaseUser") or ""
    connection_type = obj.get("connectionType") or ""
    endpoint = obj.get("endpoint") or ""
    storage_account_name = obj.get("storageAccountName") or ""

    # URL seçimi:
    # - Normal DB'lerde databaseUrl
    # - Azure Data Lake / oauth2 gibi durumlarda endpoint daha anlamlı
    url: Optional[str]
    if connection_type == "oauth2":
        url = endpoint or database_url or None
    else:
        url = database_url or endpoint or None

    # Kullanıcı seçimi:
    # - Çoğu DB'de databaseUser
    # - Bazı cloud bağlantılarında storageAccountName; yoksa None
    user: Optional[str]
    if database_user:
        user = database_user
    elif storage_account_name:
        user = storage_account_name
    else:
        user = None

    db_type = infer_db_type(name=name, database_url=url, connection_type=connection_type)

    return name, {
        "id": conn_id,
        "db_type": db_type,
        "url": url,
        "user": user,
    }


def map_connection_list_to_config(response_json: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Endpoint'ten gelen tüm connection listesini,
    connections.py'deki CONNECTIONS sözlüğüne benzeyen bir dict'e çevirir.
    """
    objects: List[Dict[str, Any]] = response_json.get("object") or []
    result: Dict[str, Dict[str, Any]] = {}

    logger.info(f"📋 Mapping {len(objects)} connection objects")
    
    skipped_count = 0
    for obj in objects:
        mapped = map_connection_object(obj)
        if not mapped:
            skipped_count += 1
            continue
        name, payload = mapped
        result[name] = payload

    logger.info(f"✅ Successfully mapped {len(result)} connections (skipped {skipped_count} invalid)")
    
    if len(result) == 0 and len(objects) > 0:
        logger.error(f"❌ All {len(objects)} connection objects were skipped! Check map_connection_object logic.")
    
    return result


def save_connections_to_json(config: Dict[str, Dict[str, Any]], filename: str = "connections_from_icc.json") -> None:
    from datetime import datetime

    root_dir = Path(__file__).resolve().parents[2]
    data_dir = root_dir / "data"
    data_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = filename[:-5] if filename.endswith(".json") else filename
    final_name = f"{base}_{timestamp}.json"

    output_path = data_dir / final_name

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(config)} connections to {output_path}")

async def fetch_and_map_connections(base_url: Optional[str] = None, auth_headers: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    ICC endpoint'inden connection list'i çekip, map_connection_list_to_config
    ile internal formata çevirip dict olarak döner.
    Uses the same authentication pattern as other repositories.
    
    Args:
        base_url: API endpoint URL (optional)
        auth_headers: Optional dict with Authorization and TokenKey headers
        
    Returns:
        Dictionary mapping connection names to their info:
        {
            "ORACLE_10": {
                "id": "4976629955435844",
                "db_type": "Oracle",
                "url": "jdbc:oracle:thin:@...",
                "user": "icc_test"
            },
            ...
        }
    """
    raw = await fetch_connection_list(base_url=base_url, auth_headers=auth_headers)
    return map_connection_list_to_config(raw)


async def populate_memory_connections(memory, base_url: Optional[str] = None, auth_headers: Optional[Dict[str, str]] = None) -> bool:
    """
    Convenience function to fetch connections from API and populate memory.connections.
    Uses the same authentication pattern as other repositories.
    
    Args:
        memory: Memory instance to populate
        base_url: API endpoint URL (optional)
        auth_headers: Optional dict with Authorization and TokenKey headers
        
    Returns:
        True if successful, False otherwise
    """
    try:
        connections = await fetch_and_map_connections(base_url=base_url, auth_headers=auth_headers)
        memory.connections = connections
        logger.info(f"✅ Populated memory with {len(connections)} connections")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to populate memory connections: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    """
    Lokal test için:
    - ICC_CONNECTION_LIST_URL env değişkenini set et
    - VPN açıksa bu script'i çalıştır
    
    Example:
        export ICC_CONNECTION_LIST_URL="https://172.16.22.13:8084/connection/list"
        python src/utils/fetch_connections.py
    """
    logging.basicConfig(level=logging.INFO)
    
    try:
        data = fetch_connection_list()
        mapped = map_connection_list_to_config(data)
        save_connections_to_json(mapped)
        print(f"\n✅ Success! Wrote {len(mapped)} connections to connections_from_icc.json")
        print(f"\nConnection names:")
        for name in sorted(mapped.keys()):
            db_type = mapped[name]['db_type']
            print(f"  - {name} ({db_type})")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. ICC_CONNECTION_LIST_URL environment variable is set")
        print("  2. You are connected to VPN")
        print("  3. The API endpoint is accessible")
