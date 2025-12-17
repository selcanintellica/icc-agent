"""
Services package for business logic layer.

This package contains service classes that handle business logic,
separating concerns from the UI layer (app.py) and data access layer (repositories).
"""

from src.services.connection_service import ConnectionService, get_connection_service
from src.services.session_manager import SessionManager, get_session_manager
from src.services.ui_formatter import UIFormatter, get_ui_formatter
from src.services.router_service import RouterService, get_router_service
from src.services.auth_service import AuthenticationService, get_auth_service
from src.services.dropdown_handler import DropdownHandler, get_dropdown_handler, init_dropdown_handler

__all__ = [
    "ConnectionService", "get_connection_service",
    "SessionManager", "get_session_manager",
    "UIFormatter", "get_ui_formatter",
    "RouterService", "get_router_service",
    "AuthenticationService", "get_auth_service",
    "DropdownHandler", "get_dropdown_handler", "init_dropdown_handler"
]
