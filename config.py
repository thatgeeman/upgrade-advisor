import os

from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEY = os.getenv("OPENAI_API_KEY", None)
if not API_KEY:
    print("⚠️ API key not found in .env file!")

# Server configuration
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT = os.getenv("GRADIO_SERVER_PORT", "7860")
GRADIO_SHARE = os.getenv("GRADIO_SHARE", "False")
