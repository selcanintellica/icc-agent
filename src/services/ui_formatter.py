"""
UI formatting service for chat messages and errors.

Extracts UI formatting logic from app.py following SOLID principles:
- Single Responsibility: Only handles UI formatting
- Open/Closed: Easy to extend with new message types
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import dash_bootstrap_components as dbc
from dash import html, dcc
from src.errors import ICCBaseError, ErrorHandler, ErrorCategory, ErrorCode

logger = logging.getLogger(__name__)


class UIFormatter:
    """
    Formats chat messages and errors for UI display.
    
    Centralizes all UI formatting logic to maintain consistent
    visual presentation and make styling changes easier.
    """
    
    @staticmethod
    def get_error_category_icon(category: ErrorCategory) -> str:
        """
        Get icon for error category.
        
        Args:
            category: Error category
            
        Returns:
            Icon string for display
        """
        icons = {
            ErrorCategory.AUTHENTICATION: "🔐",
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.VALIDATION: "⚠️",
            ErrorCategory.JOB_EXECUTION: "⚙️",
            ErrorCategory.LLM: "🤖",
            ErrorCategory.CONFIGURATION: "⚙️",
            ErrorCategory.SYSTEM: "💥",
        }
        return icons.get(category, "❌")
    
    @staticmethod
    def format_error_for_ui(error: Exception) -> Dict[str, Any]:
        """
        Format error for UI display with categorization.
        
        Args:
            error: Exception to format
            
        Returns:
            Dict with icon, code, message, retryable flag
        """
        if isinstance(error, ICCBaseError):
            return {
                "icon": UIFormatter.get_error_category_icon(error.category),
                "code": error.error_code.code,
                "message": str(error),
                "is_retryable": error.is_retryable,
            }
        
        # For non-ICC errors, convert first
        icc_error = ErrorHandler.handle(error)
        return UIFormatter.format_error_for_ui(icc_error)
    
    @staticmethod
    def format_message(role: str, content: str, timestamp: Optional[str] = None, 
                      error_info: Optional[Dict] = None, **kwargs) -> dbc.Card:
        """
        Format a chat message for display.
        
        Args:
            role: Message role (user, agent, error, etc.)
            content: Message content
            timestamp: Optional timestamp string
            error_info: Optional error information dict
            **kwargs: Additional role-specific parameters
            
        Returns:
            Dash component for display
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        if role == "user":
            return UIFormatter._format_user_message(content, timestamp)
        elif role == "agent":
            return UIFormatter._format_agent_message(content, timestamp)
        elif role == "error":
            return UIFormatter._format_error_message(content, timestamp, error_info)
        elif role == "schema_dropdown":
            return UIFormatter._format_schema_dropdown(content, timestamp, **kwargs)
        elif role == "connection_dropdown":
            return UIFormatter._format_connection_dropdown(content, timestamp, **kwargs)
        elif role == "tool_call":
            return UIFormatter._format_tool_call(content, timestamp, **kwargs)
        else:
            # Default formatting
            return UIFormatter._format_agent_message(content, timestamp)
    
    @staticmethod
    def _format_user_message(content: str, timestamp: str) -> dbc.Card:
        """Format user message."""
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("You", className="text-primary"),
                    html.Small(f" - {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-0 mt-2")
            ])
        ], className="mb-3", style={"backgroundColor": "#e3f2fd"})
    
    @staticmethod
    def _format_agent_message(content: str, timestamp: str) -> dbc.Card:
        """Format agent message."""
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("🤖 ICC Agent", className="text-success"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-0 mt-2", style={"whiteSpace": "pre-wrap"})
            ])
        ], className="mb-3", style={"backgroundColor": "#f1f8f4"})
    
    @staticmethod
    def _format_error_message(content: str, timestamp: str, 
                             error_info: Optional[Dict]) -> dbc.Card:
        """Format error message."""
        if error_info:
            icon = error_info.get("icon", "❌")
            code = error_info.get("code", "UNKNOWN")
            is_retryable = error_info.get("is_retryable", False)
            
            retry_badge = dbc.Badge(
                "Retryable" if is_retryable else "Not Retryable",
                color="warning" if is_retryable else "danger",
                className="ms-2"
            )
            
            return dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Strong(f"{icon} Error", className="text-danger"),
                        html.Small(f" • {timestamp}", className="text-muted ms-2"),
                        retry_badge
                    ]),
                    html.P([
                        html.Code(f"[{code}]", className="text-muted"),
                        html.Span(f" {content}", className="ms-2")
                    ], className="mb-0 mt-2")
                ])
            ], className="mb-3", style={"backgroundColor": "#ffebee", "borderLeft": "4px solid #f44336"})
        else:
            return dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Strong("❌ Error", className="text-danger"),
                        html.Small(f" • {timestamp}", className="text-muted ms-2")
                    ]),
                    html.P(content, className="mb-0 mt-2")
                ])
            ], className="mb-3", style={"backgroundColor": "#ffebee"})
    
    @staticmethod
    def _format_schema_dropdown(content: str, timestamp: str, **kwargs) -> dbc.Card:
        """Format schema dropdown message."""
        schemas = kwargs.get("schemas", [])
        param_name = kwargs.get("param_name", "")
        
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("🤖 ICC Agent", className="text-success"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-2 mt-2"),
                dcc.Dropdown(
                    id={"type": "schema-selector", "param": param_name},
                    options=[{"label": schema, "value": schema} for schema in schemas],
                    placeholder="Select a schema...",
                    className="mt-2",
                    style={"marginBottom": "10px"}
                ),
                dbc.Button(
                    "Confirm Selection",
                    id={"type": "schema-confirm", "param": param_name},
                    color="primary",
                    size="sm",
                    className="mt-2"
                )
            ])
        ], className="mb-3", style={"backgroundColor": "#fff3e0", "borderLeft": "4px solid #ff9800"})
    
    @staticmethod
    def _format_connection_dropdown(content: str, timestamp: str, **kwargs) -> dbc.Card:
        """Format connection dropdown message."""
        connections = kwargs.get("connections", [])
        param_name = kwargs.get("param_name", "")
        
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("🤖 ICC Agent", className="text-success"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-2 mt-2"),
                dcc.Dropdown(
                    id={"type": "connection-selector", "param": param_name},
                    options=[{"label": conn, "value": conn} for conn in connections],
                    placeholder="Select a connection...",
                    className="mt-2",
                    style={"marginBottom": "10px"}
                ),
                dbc.Button(
                    "Confirm Selection",
                    id={"type": "connection-confirm", "param": param_name},
                    color="primary",
                    size="sm",
                    className="mt-2"
                )
            ])
        ], className="mb-3", style={"backgroundColor": "#e8f5e9", "borderLeft": "4px solid #4caf50"})
    
    @staticmethod
    def _format_tool_call(content: str, timestamp: str, **kwargs) -> dbc.Card:
        """Format tool call message."""
        tool_name = kwargs.get("tool_name", "")
        status = kwargs.get("status", "running")
        
        status_colors = {
            "running": "info",
            "success": "success",
            "error": "danger"
        }
        
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("⚙️ Tool Call", className="text-info"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2"),
                    dbc.Badge(tool_name, color=status_colors.get(status, "secondary"), className="ms-2")
                ]),
                html.P(content, className="mb-0 mt-2")
            ])
        ], className="mb-3", style={"backgroundColor": "#e3f2fd"})


# Global formatter instance (singleton pattern)
_ui_formatter: Optional[UIFormatter] = None


def get_ui_formatter() -> UIFormatter:
    """
    Get or create the global UI formatter instance.
    
    Returns:
        UIFormatter: Global formatter instance
    """
    global _ui_formatter
    if _ui_formatter is None:
        _ui_formatter = UIFormatter()
        logger.info("Created global UIFormatter instance")
    return _ui_formatter
