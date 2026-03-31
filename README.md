# Firestore MCP Server

A simple MCP server that exposes Google Firestore read/write tools to an agent.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then add it to your PATH permanently (bash):

```bash
echo 'source $HOME/.local/bin/env' >> ~/.bash_profile
source ~/.bash_profile
```

## Setup

Clone the repo and navigate to the project directory:

```bash
cd vanilla
```

Install dependencies and create the virtual environment:

```bash
uv sync
```

## Activate the environment

```bash
source .venv/bin/activate
```

Your prompt will show `(vanilla)` when the environment is active.

To deactivate:

```bash
deactivate
```

## Verify installation

```bash
uv pip show firebase-admin
uv pip show mcp
```

## Configuration

Set your Firebase service account credentials before running the server:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
```

## Run the server

```bash
python firestore_mcp_server.py
```

## Register with an MCP agent

Add the following to your agent's MCP config:

```json
{
  "mcpServers": {
    "firestore": {
      "command": "python3",
      "args": ["/path/to/vanilla/firestore_mcp_server.py"]
    }
  }
}
```
