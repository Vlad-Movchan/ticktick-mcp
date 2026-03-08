from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ticktick_mcp.auth import exchange_code, get_auth_url, save_tokens

mcp = FastMCP("auth")


@mcp.tool
def ticktick_authorize(code: str | None = None) -> dict:
    """Authorize with TickTick via OAuth 2.0.

    Call with no arguments to get the authorization URL. Open that URL in your
    browser, approve access, then copy the `code` query parameter from the
    redirect URL and call this tool again with that code.

    Args:
        code: The authorization code from the OAuth redirect URL. Omit to get
              the authorization URL.
    """
    if code is None:
        try:
            url = get_auth_url()
        except ValueError as e:
            raise ToolError(str(e))
        return {
            "action": "visit_url",
            "url": url,
            "instructions": (
                "1. Open the URL above in your browser.\n"
                "2. Log in and approve access.\n"
                "3. You will be redirected to http://localhost?code=<CODE>&...\n"
                "4. Copy the value of the `code` parameter.\n"
                "5. Call ticktick_authorize(code='<CODE>') to complete authorization."
            ),
        }

    try:
        tokens = exchange_code(code)
        save_tokens(tokens)
    except Exception as e:
        raise ToolError(f"Authorization failed: {e}")

    return {"success": True, "message": "Authorization complete. Tokens saved."}
