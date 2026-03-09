import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from productivity_mcp.providers import ticktick

load_dotenv()

PROVIDERS = [ticktick]

# Determine base URL for OAuth metadata and callbacks
_port = int(os.environ.get("MCP_PORT", "8000"))
_base_url = os.environ.get("MCP_BASE_URL", f"http://localhost:{_port}")

from productivity_mcp.providers.ticktick.oauth_server import TickTickOAuthProvider  # noqa: E402

_oauth_provider = TickTickOAuthProvider(base_url=_base_url)

mcp = FastMCP("productivity-mcp", auth=_oauth_provider)


@mcp.custom_route("/callback", methods=["GET"])
async def ticktick_oauth_callback(request: Request) -> Response:
    """Receive the TickTick OAuth redirect and complete the MCP authorization flow."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if not state:
        return Response("Missing state parameter", status_code=400)

    if error:
        redirect_url = await _oauth_provider.handle_ticktick_error(error, state)
        if redirect_url is None:
            return Response("Unknown or expired state", status_code=400)
        return RedirectResponse(redirect_url)

    if not code:
        return Response("Missing code parameter", status_code=400)

    redirect_url = await _oauth_provider.handle_ticktick_callback(code, state)
    if redirect_url is None:
        return Response("Unknown or expired state", status_code=400)
    return RedirectResponse(redirect_url)


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

    redirect_uri = os.environ.get("TICKTICK_REDIRECT_URI", "")
    if not redirect_uri.endswith("/callback"):
        logging.basicConfig(level=logging.INFO)
        logger.warning(
            "TICKTICK_REDIRECT_URI=%r does not end with '/callback'. "
            "The MCP OAuth flow will not work correctly. "
            "Set it to e.g. http://localhost:%d/callback",
            redirect_uri,
            port,
        )

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting productivity-mcp on %s:%d (streamable-HTTP)", host, port)

    mcp.run(transport="streamable-http", host=host, port=port)
