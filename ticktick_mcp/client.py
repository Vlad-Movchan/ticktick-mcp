import httpx

from ticktick_mcp.auth import get_valid_token

BASE_URL = "https://api.ticktick.com/open/v1"


def request(method: str, path: str, **kwargs) -> dict | list:
    token = get_valid_token()
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    with httpx.Client() as client:
        response = client.request(
            method,
            BASE_URL + path,
            headers=headers,
            **kwargs,
        )

    if response.is_error:
        raise RuntimeError(
            f"TickTick API error {response.status_code}: {response.text}"
        )

    if response.content:
        return response.json()
    return {}
