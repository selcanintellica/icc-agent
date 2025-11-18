"""
ICC Agent Chat Interface using Plotly Dash

A simple web-based chat interface to test the ICC agent with a 7B local LLM.

Run this file to start the chat interface:
    python app.py

Then open your browser to: http://localhost:8050
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime
import uuid
import asyncio
import json
import logging

# Configure logging to see agent actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,  # Force reconfiguration of logging
    handlers=[
        logging.StreamHandler()  # Explicitly output to console
    ]
)
# Set logging for LangChain and LangGraph
logging.getLogger("langchain").setLevel(logging.DEBUG)
logging.getLogger("langgraph").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Print to console directly to ensure visibility
print("\n" + "="*60)
print("🔍 LOGGING ENABLED - You should see agent actions below")
print("="*60 + "\n")

# ICC Agent imports - Using Staged Router
from src.ai.router import handle_turn, Memory

# Initialize the Dash app with a nice theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "ICC Agent Chat"

# Session memory storage (in production, use Redis or DB)
session_memories = {}


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


async def invoke_router_async(user_message, session_id="default-session"):
    """Invoke the staged router with memory"""
    try:
        # Use both print and logging for maximum visibility
        print("\n" + "="*60)
        print(f"🔵 USER QUERY: {user_message}")
        print(f"🧵 Session ID: {session_id}")
        print("="*60)
        
        logger.info(f"🔵 User query: {user_message}")
        logger.info(f"🧵 Session ID: {session_id}")
        
        # Get or create memory for this session
        if session_id not in session_memories:
            session_memories[session_id] = Memory()
            # TODO: In production, set connection from UI selection:
            # session_memories[session_id].connection = selected_connection_from_ui
            logger.info(f"🆕 Created new memory for session: {session_id}")
            logger.info(f"🔌 Using connection: {session_memories[session_id].connection}")
        
        memory = session_memories[session_id]
        
        logger.info(f"📍 Current stage: {memory.stage.value}")
        
        # Call the router
        updated_memory, response_text = await handle_turn(memory, user_message)
        
        # Update session memory
        session_memories[session_id] = updated_memory
        
        print("\n✅ ROUTER RESPONSE:")
        print(f"� New stage: {updated_memory.stage.value}")
        print(f"💬 Response: {response_text[:200]}...")
        
        logger.info(f"✅ Router completed")
        logger.info(f"� New stage: {updated_memory.stage.value}")
        
        return {
            "response": response_text,
            "stage": updated_memory.stage.value,
            "memory": updated_memory.to_dict()
        }
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        logger.error(f"❌ Error in router: {str(e)}", exc_info=True)
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
        # Initial load - start the conversation
        welcome_message = {
            "role": "agent",
            "content": "👋 Hello! I'm the ICC Agent with staged conversation flow.\n\nI'll guide you through:\n1️⃣ Creating SQL queries\n2️⃣ Executing them\n3️⃣ Writing results or sending emails\n\nWhat SQL query would you like to execute?",
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
        logger.info(f"💬 Processing user input: {user_input}")
        
        # Invoke router with session memory
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(invoke_router_async(user_input, session_id="web-chat-session"))
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
            # Router returns a simple text response
            response_text = response.get("response", "")
            current_stage = response.get("stage", "unknown")
            
            print(f"\n� Router response: {response_text[:200]}...")
            print(f"📍 Current stage: {current_stage}")
            
            logger.info(f"💬 Router response: {response_text[:100]}...")
            logger.info(f"� Current stage: {current_stage}")
            
            # Add agent response
            agent_message = {
                "role": "agent",
                "content": response_text,
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
    
    # Disable Dash's dev tools console logging that might interfere
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    logger.info("✅ Logging initialized - Agent actions will be printed here")
    
    app.run(debug=True, host="0.0.0.0", port=8050, dev_tools_silence_routes_logging=False)
