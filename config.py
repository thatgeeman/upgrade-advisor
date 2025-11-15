import os

from dotenv import load_dotenv

load_dotenv()

# GitHub MCP configuration
GITHUB_PAT = os.getenv("GITHUB_PAT", None)
if not GITHUB_PAT:
    print("⚠️ GitHub PAT not found in .env file!")

HF_TOKEN = os.getenv("HF_TOKEN", None)
if not HF_TOKEN:
    print("⚠️ Hugging Face token not found in .env file!")

GITHUB_TOOLSETS = os.getenv("GITHUB_TOOLSETS", "repos")


# Server configuration
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT = os.getenv("GRADIO_SERVER_PORT", "7860")
GRADIO_SHARE = os.getenv("GRADIO_SHARE", "False")
