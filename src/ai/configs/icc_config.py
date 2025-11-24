import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from src.ai.toolkits.toolkits import Toolkits
from src.ai.prompts.prompts import Prompts
from langgraph.checkpoint.memory import MemorySaver
import logging

# Configure logging for LangChain and LangGraph
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable LangChain debug mode to see all agent actions
os.environ["LANGCHAIN_VERBOSE"] = "true"

load_dotenv(override=True)  # override=True forces .env to override system variables

class ICCAgentConfig:
	@staticmethod
	def get_config():
		logger.info("🚀 Initializing ICC Agent Configuration")
		logger.info(f"📊 Model: {os.getenv('MODEL_NAME', 'qwen3:1.7b')}")
		logger.info(f"🛠️  Tools loaded: {len(Toolkits.icc_toolkit)}")
		
		return {
			"prompt": Prompts.icc_prompt,
			"model": ChatOllama(
				model=os.getenv("MODEL_NAME", "qwen3:1.7b"),  # Smaller model to save GPU
				validate_model_on_init=True,
				temperature=1.0,
				seed=42,
				reasoning=False,
				num_ctx=16000,  # Reduced context window
				max_tokens=4096,
				base_url="http://localhost:11434",
				verbose=True,  # Enable verbose mode for detailed logging
			),
			"tools": Toolkits.icc_toolkit,
			"checkpointer": MemorySaver(),
		}
