import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from ticktick_mcp.tools import auth_tools, projects, tasks

load_dotenv()

mcp = FastMCP("ticktick-mcp")
mcp.mount(auth_tools.mcp)
mcp.mount(tasks.mcp)
mcp.mount(projects.mcp)

logger = logging.getLogger(__name__)


def main() -> None:
    missing = [v for v in ("TICKTICK_CLIENT_ID", "TICKTICK_CLIENT_SECRET") if not os.environ.get(v)]
    if missing:
        print(
            f"Error: missing required environment variable(s): {', '.join(missing)}\n"
            "Set them in a .env file or export them before starting the server.",
            file=sys.stderr,
        )
        sys.exit(1)

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ticktick-mcp on %s:%d (SSE)", host, port)

    mcp.run(transport="sse", host=host, port=port)
