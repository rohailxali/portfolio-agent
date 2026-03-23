import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_lead(client: AsyncClient):
    resp = await client.post(
        "/api/v1/leads",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "I'd like to hire you for a React project.",
            "source": "contact_form",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "received"


@pytest.mark.asyncio
async def test_submit_lead_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/leads",
        json={"name": "Bob", "email": "not-an-email", "message": "test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_leads_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/leads")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_leads(client: AsyncClient, auth_headers):
    # Create a lead first
    await client.post(
        "/api/v1/leads",
        json={"name": "Carol", "email": "carol@example.com", "message": "Hello"},
    )
    resp = await client.get("/api/v1/leads", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_update_lead_status(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/leads",
        json={"name": "Dave", "email": "dave@example.com", "message": "Interested"},
    )
    lead_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "contacted"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "contacted"


@pytest.mark.asyncio
async def test_update_lead_invalid_status(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/leads",
        json={"name": "Eve", "email": "eve@example.com"},
    )
    lead_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "hacked"},
        headers=auth_headers,
    )
    assert resp.status_code == 400