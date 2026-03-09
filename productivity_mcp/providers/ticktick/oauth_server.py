"""TickTick OAuth 2.1 Authorization Server provider for MCP.

Brokers the TickTick OAuth flow: acts as an OAuth AS to MCP clients, and as an
OAuth client to TickTick. All state (clients, codes, tokens) is in-memory.
"""

import secrets
import time
from urllib.parse import urlencode

from fastmcp.server.auth import AccessToken, OAuthProvider
from mcp.server.auth.handlers.register import ClientRegistrationOptions
from mcp.server.auth.provider import AuthorizationCode, AuthorizationParams, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from productivity_mcp.providers.ticktick.auth import exchange_code, save_tokens
from productivity_mcp.providers.ticktick.config import get_settings

_TICKTICK_AUTH_URL = "https://ticktick.com/oauth/authorize"
_TICKTICK_SCOPE = "tasks:read tasks:write"
_AUTH_CODE_TTL = 600  # 10 minutes
_ACCESS_TOKEN_TTL = 3600  # 1 hour


class TickTickOAuthProvider(OAuthProvider):
    """OAuth 2.1 Authorization Server that brokers TickTick auth for MCP clients."""

    def __init__(self, base_url: str) -> None:
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )
        # In-memory stores
        self._clients: dict[str, OAuthClientInformationFull] = {}
        # ticktick_state → (client, AuthorizationParams)
        self._pending_states: dict[str, tuple[OAuthClientInformationFull, AuthorizationParams]] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}

    # ------------------------------------------------------------------ #
    # Client registry                                                      #
    # ------------------------------------------------------------------ #

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    # ------------------------------------------------------------------ #
    # Authorization                                                         #
    # ------------------------------------------------------------------ #

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Redirect the MCP client's browser to TickTick's authorization page."""
        ticktick_state = secrets.token_urlsafe(32)
        self._pending_states[ticktick_state] = (client, params)

        settings = get_settings()
        qs = urlencode(
            {
                "client_id": settings.TICKTICK_CLIENT_ID,
                "response_type": "code",
                "scope": _TICKTICK_SCOPE,
                "redirect_uri": settings.TICKTICK_REDIRECT_URI,
                "state": ticktick_state,
            }
        )
        return f"{_TICKTICK_AUTH_URL}?{qs}"

    async def handle_ticktick_callback(self, code: str, state: str) -> str | None:
        """Complete the TickTick OAuth flow and return the MCP client redirect URL.

        Returns the redirect URL on success, or None if the state is unknown.
        """
        entry = self._pending_states.pop(state, None)
        if entry is None:
            return None
        client, params = entry

        # Exchange TickTick code for TickTick tokens and persist them
        tokens = exchange_code(code)
        save_tokens(tokens)

        # Issue MCP authorization code
        mcp_code = secrets.token_urlsafe(32)
        self._auth_codes[mcp_code] = AuthorizationCode(
            code=mcp_code,
            scopes=params.scopes or [],
            expires_at=time.time() + _AUTH_CODE_TTL,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
        )

        # Build redirect back to the MCP client
        redirect_params: dict[str, str] = {"code": mcp_code}
        if params.state:
            redirect_params["state"] = params.state
        return f"{params.redirect_uri}?{urlencode(redirect_params)}"

    async def handle_ticktick_error(self, error: str, state: str) -> str | None:
        """Handle a TickTick OAuth error and return the MCP client redirect URL."""
        entry = self._pending_states.pop(state, None)
        if entry is None:
            return None
        _, params = entry
        error_params: dict[str, str] = {"error": error}
        if params.state:
            error_params["state"] = params.state
        return f"{params.redirect_uri}?{urlencode(error_params)}"

    # ------------------------------------------------------------------ #
    # Authorization code exchange                                          #
    # ------------------------------------------------------------------ #

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        return self._auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        self._auth_codes.pop(authorization_code.code, None)

        access_token_str = secrets.token_hex(32)
        refresh_token_str = secrets.token_hex(32)
        expires_in = _ACCESS_TOKEN_TTL

        self._access_tokens[access_token_str] = AccessToken(
            token=access_token_str,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + expires_in,
        )
        self._refresh_tokens[refresh_token_str] = RefreshToken(
            token=refresh_token_str,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
        )

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_str,
            scope=" ".join(authorization_code.scopes) or None,
        )

    # ------------------------------------------------------------------ #
    # Token management                                                     #
    # ------------------------------------------------------------------ #

    async def load_access_token(self, token: str) -> AccessToken | None:
        at = self._access_tokens.get(token)
        if at is None:
            return None
        if at.expires_at is not None and time.time() > at.expires_at:
            self._access_tokens.pop(token, None)
            return None
        return at

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        rt = self._refresh_tokens.get(refresh_token)
        if rt is None or rt.client_id != client.client_id:
            return None
        return rt

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._refresh_tokens.pop(refresh_token.token, None)

        new_scopes = scopes if scopes else refresh_token.scopes
        access_token_str = secrets.token_hex(32)
        new_refresh_str = secrets.token_hex(32)
        expires_in = _ACCESS_TOKEN_TTL

        self._access_tokens[access_token_str] = AccessToken(
            token=access_token_str,
            client_id=client.client_id,
            scopes=new_scopes,
            expires_at=int(time.time()) + expires_in,
        )
        self._refresh_tokens[new_refresh_str] = RefreshToken(
            token=new_refresh_str,
            client_id=client.client_id,
            scopes=new_scopes,
        )

        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=new_refresh_str,
            scope=" ".join(new_scopes) or None,
        )
