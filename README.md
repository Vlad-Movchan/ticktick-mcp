# productivity-mcp

A universal MCP server that lets AI assistants (Claude, etc.) manage productivity tools via their APIs. Currently ships a TickTick integration; designed to add more providers without touching core server code.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- TickTick developer credentials ([create an app](https://developer.ticktick.com/manage))

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure credentials

Create a `.env` file in the project root:

```env
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_client_secret
```

### 3. Authorize with TickTick

Run the authorization flow through your MCP client by calling the `ticktick_authorize` tool:

1. Call `ticktick_authorize` with no arguments — the tool returns an authorization URL.
2. Open the URL in your browser and approve access.
3. You will be redirected to `http://localhost?code=<CODE>&...` (the page won't load — that's expected).
4. Copy the `code` value from the URL.
5. Call `ticktick_authorize(code="<CODE>")` to exchange it for tokens.

Tokens are saved to `~/.ticktick-mcp/tokens.json` (permissions `600`) and auto-refreshed on each request.

To use a different token path:

```env
TICKTICK_TOKEN_PATH=/path/to/tokens.json
```

## Running the server

### Docker (recommended)

```bash
docker compose up --build
```

The server starts on `http://localhost:8000/sse`. Tokens are persisted in a named Docker volume (`ticktick-tokens`) and survive container restarts.

### Local (uv)

```bash
uv run productivity-mcp
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "productivity": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ticktick-mcp", "run", "productivity-mcp"],
      "env": {
        "TICKTICK_CLIENT_ID": "your_client_id",
        "TICKTICK_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add productivity -- uv --directory /absolute/path/to/ticktick-mcp run productivity-mcp
```

Set credentials in `.env` or export them before launching Claude Code.

## Available tools

| Tool | Description |
|------|-------------|
| `ticktick_authorize` | OAuth 2.0 authorization flow |
| `ticktick_list_projects` | List all projects |
| `ticktick_get_project_tasks` | Get tasks in a project |
| `ticktick_create_task` | Create a new task |
| `ticktick_get_task` | Get task details |
| `ticktick_update_task` | Update task fields |
| `ticktick_complete_task` | Mark a task as complete |
| `ticktick_delete_task` | Delete a task |

## Adding a new provider

1. Create `productivity_mcp/providers/<name>/` with your integration code.
2. Expose `REQUIRED_ENV_VARS: list[str]` and `register(mcp: FastMCP) -> None` in its `__init__.py`.
3. Add it to `PROVIDERS` in `productivity_mcp/server.py`.

The server will automatically validate its env vars at startup and mount its tools.

## Security

Token file permissions are set to `600` on creation. Never commit `.env` or token files to version control.
