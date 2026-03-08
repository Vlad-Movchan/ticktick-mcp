import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from productivity_mcp.providers import ticktick

load_dotenv()

PROVIDERS = [ticktick]

mcp = FastMCP("productivity-mcp")

for provider in PROVIDERS:
    provider.register(mcp)

logger = logging.getLogger(__name__)


def main() -> None:
    missing = [
        var
        for provider in PROVIDERS
        for var in provider.REQUIRED_ENV_VARS
        if not os.environ.get(var)
    ]
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
    logger.info("Starting productivity-mcp on %s:%d (SSE)", host, port)

    mcp.run(transport="sse", host=host, port=port)
