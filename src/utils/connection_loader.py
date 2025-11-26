"""
Helper module for loading and managing dynamic connection data.
This module provides utilities to work with connection data fetched from API.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def format_connection_data(api_response: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Convert API response to the format expected by Memory.connections.
    
    Assumes API returns a list of connection objects with structure like:
    [
        {
            "name": "ORACLE_10",
            "id": "4976629955435844",
            "db_type": "Oracle",
            "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
            "user": "icc_test"
        },
        ...
    ]
    
    Args:
        api_response: List of connection dictionaries from API
        
    Returns:
        Dictionary mapping connection names to their full info:
        {
            "ORACLE_10": {
                "id": "4976629955435844",
                "db_type": "Oracle",
                "url": "jdbc:oracle:thin:@172.16.44.10:1521:ORCL19C",
                "user": "icc_test"
            },
            ...
        }
    """
    connections = {}
    
    for conn in api_response:
        name = conn.get("name")
        if not name:
            logger.warning(f"⚠️ Connection missing 'name' field, skipping: {conn}")
            continue
            
        connections[name] = {
            "id": conn.get("id", ""),
            "db_type": conn.get("db_type", "Unknown"),
            "url": conn.get("url"),
            "user": conn.get("user")
        }
    
    logger.info(f"✅ Formatted {len(connections)} connections from API")
    return connections


def get_connection_names(connections: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Extract list of connection names from formatted connection data.
    
    Args:
        connections: Dictionary of connections
        
    Returns:
        List of connection names
    """
    return list(connections.keys())


def format_connections_for_display(connections: Dict[str, Dict[str, Any]]) -> str:
    """
    Format connections as a user-friendly string for display.
    
    Args:
        connections: Dictionary of connections
        
    Returns:
        Formatted string listing all connections
    """
    if not connections:
        return "No connections available."
    
    lines = ["Available connections:"]
    for name, info in connections.items():
        db_type = info.get("db_type", "Unknown")
        lines.append(f"• {name} ({db_type})")
    
    return "\n".join(lines)


def validate_connection_exists(
    connection_name: str, 
    connections: Dict[str, Dict[str, Any]]
) -> bool:
    """
    Check if a connection name exists in the connections dictionary.
    
    Args:
        connection_name: Name to check
        connections: Dictionary of connections
        
    Returns:
        True if connection exists, False otherwise
    """
    return connection_name in connections


# Example usage:
"""
# After fetching from API and converting the response:
api_connections = fetch_connections_from_api()  # Your API call
formatted_connections = format_connection_data(api_connections)

# Set in memory:
memory.connections = formatted_connections

# Now memory can get connection IDs:
connection_id = memory.get_connection_id("ORACLE_10")

# Format for user display:
display_text = format_connections_for_display(memory.connections)
# or use the built-in method:
display_text = memory.get_connection_list_for_llm()
"""
