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
# Instructions 

1. Create a scoped Personal Access Token from GitHub from https://github.com/settings/personal-access-tokens/new with the following scopes, that allows access for public repositories. 
2. Store as GITHUB_PAT in a .env file in the root directory of the project.

TO-DO

3. Inspector: `npx @modelcontextprotocol/inspector`, accessible at `http://localhost:6274` 


## Running the MCP Server Locally      
Launch the server with the command (using `podman` here) 
``` 
podman run -i --rm \
-e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT \
-e GITHUB_READ_ONLY=1 \
-e GITHUB_TOOLSETS="default"  
ghcr.io/github/github-mcp-server
``` 
Connecting to `Continue` Extension from VSCode: TODO


## Running MCP With VSCode configuration
```{
    "inputs": [
        {
            "type": "promptString",
            "id": "github_token",
            "description": "GitHub Personal Access Token",
            "password": true
        }
    ],
    "servers": {
        "github": {
            "command": "podman",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "-e",
                "GITHUB_READ_ONLY=1",
                "-e",
                "GITHUB_TOOLSETS=default",
                "ghcr.io/github/github-mcp-server"
            ],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "${input:github_token}"
                "GITHUB_READ_ONLY": "1",
                "GITHUB_TOOLSETS": "default",
            }
        }
    }
}```




