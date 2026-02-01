---
title: FixMyEnv Agent
emoji: 🐍
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.0.1
app_file: app.py
pinned: false
license: mit
short_description: MCP for Agents that plan your python package upgrade
hf_oauth: true
hf_oauth_scopes:
  - read-repos
tags:
  - building-mcp-track-enterprise
  - building-mcp-track-customer
  - mcp-in-action-track-customer
  - mcp-in-action-track-enterprise
---

# FixMyEnv: Package Upgrade Advisor

An AI-powered Gradio app (and MCP server) that analyzes your Python project,
finds outdated or vulnerable dependencies, and recommends upgrades. Attach a
`pyproject.toml` or `requirements.txt`, chat with the agent, and it will pull
package data via GitHub MCP and run `uv` resolution to suggest safe versions.

- App: https://huggingface.co/spaces/MCP-1st-Birthday/FixMyEnv 
- Demo Video: https://www.youtube.com/watch?v=u1-gZqPu0R0 
- Social Post: [LinkedIn](https://www.linkedin.com/posts/thatgeeman_mcp-hackathon-aiagents-activity-7401044891281235968-iSSw)

Demo Video: https://www.youtube.com/watch?v=u1-gZqPu0R0 
Social Post: [LinkedIn](https://www.linkedin.com/posts/thatgeeman_mcp-hackathon-aiagents-activity-7401044891281235968-iSSw)

## What you get
- Gradio chat UI with file uploads for dependency manifests.
- Smolagents-based reasoning backed by Hugging Face Inference API.
- GitHub MCP client for package metadata; `uv` for dependency resolution.
- Runs locally with your own tokens; can also be served from Hugging Face Spaces.

## Prerequisites
- Python 3.10+
- `git` and a virtual environment tool (`python -m venv` works fine)
- Hugging Face access token with Inference API rights (`HF_TOKEN`)
- GitHub Personal Access Token with public repo read scope (`GITHUB_PAT`)
- Optional: Podman or Docker if you want to run the GitHub MCP server locally instead of using the hosted Copilot MCP endpoint.

## Setup
1. Clone and enter the repo:
   ```bash
   git clone <your-fork-url> upgrade-advisor
   cd upgrade-advisor
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies (editable mode so local changes are picked up):
   ```bash
   pip install -e .
   ```
   Alternatively: `pip install -r requirements.txt`.
4. Create a `.env` in the project root:
   ```dotenv
   GITHUB_PAT=ghp_********************************
   HF_TOKEN=hf_***********************************
   # Optional tweaks
   GITHUB_TOOLSETS="repos"      # or "default,discussions" 
   GITHUB_READ_ONLY=1
   AGENT_MODEL=Qwen/Qwen3-Next-80B-A3B-Thinking
   HF_INFERENCE_PROVIDER=together
   GRADIO_SERVER_NAME=0.0.0.0
   GRADIO_SERVER_PORT=7860
   ```
   The app will warn on missing tokens but will not function fully without
   them.
   As of 2025-12-20 the toolsets from Github MCP are experimental. Please
   double check for available tools [here](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md#remote-mcp-toolsets)

## Run the app
```bash
python app.py
```
- Gradio starts at `http://127.0.0.1:7860` by default.
- Sign in with your Hugging Face account when prompted (or rely on `HF_TOKEN`).
- Ask upgrade questions and optionally upload `pyproject.toml` or `requirements.txt`.
- Uploaded files are placed in `uploads/` for the session and cleaned up on exit.

## Optional: run the GitHub MCP server locally
The app defaults to the hosted Copilot MCP endpoint. To use a local MCP server instead:
```bash
podman run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT \
  -e GITHUB_READ_ONLY=1 \
  -e GITHUB_TOOLSETS="default" \
  ghcr.io/github/github-mcp-server
```
Update `app.py` to point to your local MCP server URL/transport if you take
this route.
Read more about GitHub MCP server setup [here](https://github.com/github/github-mcp-server).

## Developing and testing
- Code lives in `src/upgrade_advisor/`; the Gradio entry point is `app.py`.
- Tooling and prompts for the agent are under `src/upgrade_advisor/agents/`.
- Basic samples for dependency files are in `tests/`.
- Run checks (none yet by default): `pytest`.

## Troubleshooting
- **Missing tokens**: ensure `GITHUB_PAT` and `HF_TOKEN` are in `.env` or your shell.
- **Model choice**: set `AGENT_MODEL`/`CHAT_MODEL` if you want to swap the default Qwen model.
- **Port conflicts**: override `GRADIO_SERVER_PORT` in `.env`.



