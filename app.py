"""
ICC Agent Chat Interface using Plotly Dash

A simple web-based chat interface to test the ICC agent with a 7B local LLM.

Run this file to start the chat interface:
    python app.py

Then open your browser to: http://localhost:8050
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime
import uuid
import asyncio
import json

# ICC Agent imports
from langgraph.prebuilt import create_react_agent
from src.ai.configs.icc_config import ICCAgentConfig


# Initialize the Dash app with a nice theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "ICC Agent Chat"

# Initialize the ICC agent
agent_config = ICCAgentConfig.get_config()
icc_agent = create_react_agent(**agent_config)


# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("🤖 ICC Agent Chat Interface", className="text-center mt-4 mb-4"),
            html.P(
                "Chat with the ICC Agent to create database jobs. Try queries like: "
                "'Get customers from USA' or 'Email sales data to manager@example.com'",
                className="text-center text-muted mb-4"
            )
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            # Chat history display
            dbc.Card([
                dbc.CardBody([
                    html.Div(
                        id="chat-history",
                        style={
                            "height": "500px",
                            "overflowY": "auto",
                            "padding": "20px",
                            "backgroundColor": "#f8f9fa"
                        }
                    )
                ])
            ], className="mb-3")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            # Input area
            dbc.InputGroup([
                dbc.Input(
                    id="user-input",
                    placeholder="Type your message here... (e.g., 'Get customers from USA')",
                    type="text",
                    style={"fontSize": "16px"}
                ),
                dbc.Button(
                    "Send",
                    id="send-button",
                    color="primary",
                    n_clicks=0
                )
            ])
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(
                id="status-indicator",
                className="mt-2 text-center text-muted"
            )
        ])
    ]),
    
    # Hidden div to store chat messages
    dcc.Store(id="chat-store", data=[]),
    
    # Example queries
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("💡 Example Queries:", className="mt-4 mb-2"),
                dbc.ButtonGroup([
                    dbc.Button("Get customers from USA", id="example-1", color="secondary", outline=True, size="sm", className="me-2 mb-2"),
                    dbc.Button("Show active orders", id="example-2", color="secondary", outline=True, size="sm", className="me-2 mb-2"),
                    dbc.Button("Email data to test@example.com", id="example-3", color="secondary", outline=True, size="sm", className="mb-2"),
                ])
            ])
        ])
    ])
    
], fluid=True, style={"maxWidth": "1000px"})


def format_message(role, content, timestamp=None):
    """Format a chat message for display"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%H:%M:%S")
    
    if role == "user":
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("You", className="text-primary"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-0 mt-2")
            ])
        ], className="mb-3", style={"backgroundColor": "#e3f2fd"})
    
    elif role == "agent":
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("🤖 ICC Agent", className="text-success"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.P(content, className="mb-0 mt-2", style={"whiteSpace": "pre-wrap"})
            ])
        ], className="mb-3", style={"backgroundColor": "#f1f8e9"})
    
    elif role == "error":
        return dbc.Alert(
            [
                html.Strong("⚠️ Error: "),
                content
            ],
            color="danger",
            className="mb-3"
        )
    
    elif role == "tool":
        return dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Strong("🔧 Tool Call", className="text-info"),
                    html.Small(f" • {timestamp}", className="text-muted ms-2")
                ]),
                html.Pre(
                    content,
                    className="mb-0 mt-2",
                    style={"fontSize": "12px", "backgroundColor": "#263238", "color": "#aed581", "padding": "10px", "borderRadius": "5px"}
                )
            ])
        ], className="mb-3")


async def invoke_agent_async(user_message, thread_id="default-session"):
    """Invoke the agent asynchronously with memory"""
    try:
        response = icc_agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": thread_id}}
        )
        return response
    except Exception as e:
        return {"error": str(e)}


@app.callback(
    [Output("chat-history", "children"),
     Output("chat-store", "data"),
     Output("user-input", "value"),
     Output("status-indicator", "children")],
    [Input("send-button", "n_clicks"),
     Input("example-1", "n_clicks"),
     Input("example-2", "n_clicks"),
     Input("example-3", "n_clicks"),
     Input("user-input", "n_submit")],
    [State("user-input", "value"),
     State("chat-store", "data")]
)
def update_chat(send_clicks, ex1_clicks, ex2_clicks, ex3_clicks, submit, user_input, chat_data):
    """Handle chat interactions"""
    ctx = callback_context
    
    if not ctx.triggered:
        # Initial load
        welcome_message = {
            "role": "agent",
            "content": "👋 Hello! I'm the ICC Agent. I can help you create database jobs. Try asking me to get data, save results, or send emails!",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        return [format_message(**welcome_message)], [welcome_message], "", ""
    
    # Determine which button was clicked
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Handle example button clicks
    if button_id == "example-1":
        user_input = "Get customers from USA"
    elif button_id == "example-2":
        user_input = "Show active orders"
    elif button_id == "example-3":
        user_input = "Email data to test@example.com"
    
    # If no input, return current state
    if not user_input or user_input.strip() == "":
        chat_display = [format_message(**msg) for msg in chat_data]
        return chat_display, chat_data, "", ""
    
    # Add user message
    timestamp = datetime.now().strftime("%H:%M:%S")
    user_message = {
        "role": "user",
        "content": user_input,
        "timestamp": timestamp
    }
    chat_data.append(user_message)
    
    # Show "thinking" status
    chat_display = [format_message(**msg) for msg in chat_data]
    
    try:
        # Invoke agent with memory (note: Dash doesn't natively support async, using sync wrapper)
        # Using a single thread_id keeps conversation history across messages
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(invoke_agent_async(user_input, thread_id="web-chat-session"))
        loop.close()
        
        if "error" in response:
            # Error response
            error_message = {
                "role": "error",
                "content": response["error"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            chat_data.append(error_message)
        else:
            # Parse agent response
            messages = response.get("messages", [])
            
            # Extract tool calls and final response
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    # Tool call message
                    for tool_call in msg.tool_calls:
                        tool_message = {
                            "role": "tool",
                            "content": json.dumps({
                                "tool": tool_call.get("name", "unknown"),
                                "args": tool_call.get("args", {})
                            }, indent=2),
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        chat_data.append(tool_message)
                
                elif hasattr(msg, "content") and msg.content and msg.content.strip():
                    # Agent's text response
                    if not any(x in str(msg.content).lower() for x in ["tool", "function_call"]):
                        agent_message = {
                            "role": "agent",
                            "content": msg.content,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        chat_data.append(agent_message)
            
            # If no messages added, add a default response
            if len(chat_data) == len([msg for msg in chat_data if msg["role"] == "user"]) + len([msg for msg in chat_data if msg["role"] == "user"]) - 1:
                agent_message = {
                    "role": "agent",
                    "content": "Task completed! Check the tool calls above for details.",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                chat_data.append(agent_message)
    
    except Exception as e:
        error_message = {
            "role": "error",
            "content": f"Failed to process request: {str(e)}",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        chat_data.append(error_message)
    
    # Update chat display
    chat_display = [format_message(**msg) for msg in chat_data]
    
    return chat_display, chat_data, "", ""


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting ICC Agent Chat Interface")
    print("=" * 60)
    print("\n📍 Open your browser to: http://localhost:8050")
    print("\n💡 Try example queries:")
    print("   - Get customers from USA")
    print("   - Show active orders")
    print("   - Email sales data to manager@example.com")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    print("=" * 60)
    
    app.run(debug=True, host="0.0.0.0", port=8050)
