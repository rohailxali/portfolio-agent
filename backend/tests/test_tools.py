import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.monitor import CheckWebsiteHealthTool
from app.tools.deploy import TriggerDeploymentTool, ListDeploymentsTool
from app.tools.memory_tools import ReadMemoryTool, WriteMemoryTool


@pytest.mark.asyncio
async def test_health_check_success(db_session: AsyncSession):
    tool = CheckWebsiteHealthTool()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.tools.monitor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with patch("app.tools.monitor._get_ssl_expiry_days", return_value=90):
            result = await tool.run(
                inputs={"url": "https://example.com"},
                db=db_session,
                user_id="00000000-0000-0000-0000-000000000001",
            )

    assert result.success is True
    assert result.data["is_up"] is True
    assert result.data["status_code"] == 200
    assert result.data["ssl_expiry_days"] == 90


@pytest.mark.asyncio
async def test_health_check_timeout(db_session: AsyncSession):
    import httpx
    tool = CheckWebsiteHealthTool()

    with patch("app.tools.monitor.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_cls.return_value = mock_client

        result = await tool.run(
            inputs={"url": "https://example.com"},
            db=db_session,
            user_id="00000000-0000-0000-0000-000000000001",
        )

    assert result.success is True  # Tool itself succeeds; is_up reflects reality
    assert result.data["is_up"] is False
    assert "timed out" in result.data["error"]


@pytest.mark.asyncio
async def test_trigger_deployment_requires_confirmation(db_session: AsyncSession):
    tool = TriggerDeploymentTool()
    result = await tool.run(
        inputs={"confirm": False, "branch": "main"},
        db=db_session,
        user_id="00000000-0000-0000-0000-000000000001",
        confirmed=False,
    )
    assert result.success is False
    assert result.requires_confirmation is True
    assert "confirm" in result.confirmation_message.lower()


@pytest.mark.asyncio
async def test_trigger_deployment_invalid_branch(db_session: AsyncSession):
    tool = TriggerDeploymentTool()
    result = await tool.run(
        inputs={"confirm": True, "branch": "main; rm -rf /"},
        db=db_session,
        user_id="00000000-0000-0000-0000-000000000001",
        confirmed=True,
    )
    assert result.success is False
    assert "Invalid branch" in result.error


@pytest.mark.asyncio
async def test_list_deployments_empty(db_session: AsyncSession):
    tool = ListDeploymentsTool()
    result = await tool.run(
        inputs={"limit": 5},
        db=db_session,
        user_id="00000000-0000-0000-0000-000000000001",
    )
    assert result.success is True
    assert isinstance(result.data["deployments"], list)


@pytest.mark.asyncio
async def test_write_and_read_memory(db_session: AsyncSession):
    write_tool = WriteMemoryTool()
    read_tool = ReadMemoryTool()
    user_id = "00000000-0000-0000-0000-000000000002"

    write_result = await write_tool.run(
        inputs={"key": "preferred_deploy_time", "value": "02:00 UTC", "category": "preference"},
        db=db_session,
        user_id=user_id,
    )
    assert write_result.success is True

    read_result = await read_tool.run(
        inputs={"key": "preferred_deploy_time"},
        db=db_session,
        user_id=user_id,
    )
    assert read_result.success is True
    assert read_result.data["value"] == "02:00 UTC"
    assert read_result.data["found"] is True


@pytest.mark.asyncio
async def test_read_missing_memory_key(db_session: AsyncSession):
    tool = ReadMemoryTool()
    result = await tool.run(
        inputs={"key": "nonexistent_key_xyz"},
        db=db_session,
        user_id="00000000-0000-0000-0000-000000000003",
    )
    assert result.success is True
    assert result.data["found"] is False
    assert result.data["value"] is None


@pytest.mark.asyncio
async def test_write_system_key_requires_confirmation(db_session: AsyncSession):
    tool = WriteMemoryTool()
    result = await tool.run(
        inputs={"key": "notification_rules", "value": {"all": False}, "confirm": False},
        db=db_session,
        user_id="00000000-0000-0000-0000-000000000002",
    )
    assert result.success is False
    assert result.requires_confirmation is True