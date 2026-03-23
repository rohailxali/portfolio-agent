import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_creates_conversation(client: AsyncClient, auth_headers):
    mock_result = {
        "reply": "Your site is up and responding in 120ms.",
        "tool_calls": [{"tool": "check_website_health", "inputs": {}}],
        "requires_confirmation": False,
        "pending_action": None,
    }
    with patch("app.agent.router.run_agent", new=AsyncMock(return_value=mock_result)):
        resp = await client.post(
            "/api/v1/agent/chat",
            json={"message": "Is my site up?"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["reply"] == "Your site is up and responding in 120ms."
    assert data["requires_confirmation"] is False


@pytest.mark.asyncio
async def test_chat_continues_conversation(client: AsyncClient, auth_headers):
    mock_result = {
        "reply": "Deployment triggered.",
        "tool_calls": [],
        "requires_confirmation": False,
        "pending_action": None,
    }
    with patch("app.agent.router.run_agent", new=AsyncMock(return_value=mock_result)):
        # First turn
        resp1 = await client.post(
            "/api/v1/agent/chat",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        conversation_id = resp1.json()["conversation_id"]

        # Second turn in same conversation
        resp2 = await client.post(
            "/api/v1/agent/chat",
            json={"message": "Deploy main", "conversation_id": conversation_id},
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conversation_id


@pytest.mark.asyncio
async def test_chat_returns_confirmation_request(client: AsyncClient, auth_headers):
    mock_result = {
        "reply": "I need confirmation to deploy. Re-send with confirm=true.",
        "tool_calls": [],
        "requires_confirmation": True,
        "pending_action": {
            "tool_name": "trigger_deployment",
            "inputs": {"branch": "main", "confirm": False},
            "confirmation_message": "Confirm deployment?",
        },
    }
    with patch("app.agent.router.run_agent", new=AsyncMock(return_value=mock_result)):
        resp = await client.post(
            "/api/v1/agent/chat",
            json={"message": "Deploy now"},
            headers=auth_headers,
        )
    data = resp.json()
    assert data["requires_confirmation"] is True
    assert data["pending_action"]["tool_name"] == "trigger_deployment"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, auth_headers):
    mock_result = {
        "reply": "ok",
        "tool_calls": [],
        "requires_confirmation": False,
        "pending_action": None,
    }
    with patch("app.agent.router.run_agent", new=AsyncMock(return_value=mock_result)):
        await client.post(
            "/api/v1/agent/chat",
            json={"message": "ping"},
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/agent/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1