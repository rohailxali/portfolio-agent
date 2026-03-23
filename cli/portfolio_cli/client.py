import httpx
from typing import Any, Optional
from portfolio_cli.config import get_api_url, get_token


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


def _headers() -> dict:
    token = get_token()
    if not token:
        raise ApiError(401, "Not authenticated. Run: portfolio auth login")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get(path: str, params: Optional[dict] = None) -> Any:
    url = f"{get_api_url()}{path}"
    with httpx.Client(timeout=20) as client:
        resp = client.get(url, headers=_headers(), params=params)
    _raise(resp)
    return resp.json()


def post(path: str, body: Optional[dict] = None, auth: bool = True) -> Any:
    url = f"{get_api_url()}{path}"
    headers = _headers() if auth else {"Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers, json=body or {})
    _raise(resp)
    if resp.status_code == 204:
        return None
    return resp.json()


def patch(path: str, body: dict) -> Any:
    url = f"{get_api_url()}{path}"
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, headers=_headers(), json=body)
    _raise(resp)
    return resp.json()


def _raise(resp: httpx.Response) -> None:
    if not resp.is_success:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise ApiError(resp.status_code, detail)