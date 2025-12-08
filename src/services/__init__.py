"""
Services package for business logic layer.

This package contains service classes that handle business logic,
separating concerns from the UI layer (app.py) and data access layer (repositories).
"""

from src.services.connection_service import ConnectionService, get_connection_service

__all__ = ["ConnectionService", "get_connection_service"]
