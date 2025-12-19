"""
Dependency Injection Container.

Centralizes dependency management and lifecycle, replacing 15+ global singletons
with proper dependency injection following Dependency Inversion Principle.

Usage:
    from src.container import get_container

    container = get_container()
    connection_service = container.connection_service()
    session_manager = container.session_manager()
"""

import logging
from dependency_injector import containers, providers

from src.utils.response_parser import ResponseParser
from src.utils.http_error_factory import HTTPErrorFactory
from src.utils.config_loader import ConfigLoader
from src.services.connection_service import ConnectionService
from src.services.session_manager import SessionManager
from src.services.ui_formatter import UIFormatter
from src.services.router_service import RouterService

logger = logging.getLogger(__name__)


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for ICC Agent application.

    Manages:
    - Utility classes (factories for stateless helpers)
    - Services (singletons for stateful business logic)
    - Repository dependencies

    Benefits:
    - Single source of truth for dependencies
    - Easy testing via dependency replacement
    - Clear dependency graph
    - Proper lifecycle management
    """

    # Configuration
    config = providers.Configuration()

    # Utilities (Factory providers - create new instances)
    # These are stateless helpers that can be instantiated as needed
    response_parser = providers.Factory(ResponseParser)

    http_error_factory = providers.Factory(
        HTTPErrorFactory,
        response_parser=response_parser
    )

    config_loader = providers.Singleton(ConfigLoader)

    # Services (Singleton providers - single instance per container)
    # These are stateful business logic components
    connection_service = providers.Singleton(
        ConnectionService
    )

    session_manager = providers.Singleton(
        SessionManager
    )

    ui_formatter = providers.Singleton(
        UIFormatter
    )

    router_service = providers.Singleton(
        RouterService
    )


# Global container instance
_container: Container = None


def get_container() -> Container:
    """
    Get or create the global dependency injection container.

    Returns:
        Container: Global container instance
    """
    global _container
    if _container is None:
        _container = Container()
        logger.info("Created global dependency injection container")
    return _container


def reset_container() -> None:
    """
    Reset the container (useful for testing).

    This allows tests to start with fresh instances.
    """
    global _container
    _container = None
    logger.info("Reset dependency injection container")
