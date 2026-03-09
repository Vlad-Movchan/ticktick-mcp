import pytest
from fastmcp.exceptions import ToolError
from productivity_mcp.providers.ticktick.tools.projects import (
    ticktick_create_project,
    ticktick_delete_project,
    ticktick_update_project,
)


@pytest.fixture
def mock_client(mocker):
    return mocker.patch("productivity_mcp.providers.ticktick.tools.projects.client.request")


def test_create_project_minimal(mock_client):
    mock_client.return_value = {"id": "p1", "name": "Work", "color": None, "kind": "TASK"}
    result = ticktick_create_project("Work")
    mock_client.assert_called_once_with("POST", "/project", json={"name": "Work"})
    assert result["id"] == "p1"
    assert result["name"] == "Work"


def test_create_project_with_color_and_kind(mock_client):
    mock_client.return_value = {"id": "p2", "name": "Notes", "color": "#ff0000", "kind": "NOTE"}
    ticktick_create_project("Notes", color="#ff0000", kind="NOTE")
    body = mock_client.call_args[1]["json"]
    assert body == {"name": "Notes", "color": "#ff0000", "kind": "NOTE"}


def test_update_project(mock_client):
    mock_client.return_value = {"id": "p1", "name": "Work v2", "color": "#00ff00", "kind": "TASK"}
    result = ticktick_update_project("p1", name="Work v2", color="#00ff00")
    mock_client.assert_called_once_with("PUT", "/project/p1", json={"name": "Work v2", "color": "#00ff00"})
    assert result["name"] == "Work v2"


def test_update_project_omits_none(mock_client):
    mock_client.return_value = {"id": "p1", "name": "Work v2", "color": None, "kind": "TASK"}
    ticktick_update_project("p1", name="Work v2")
    body = mock_client.call_args[1]["json"]
    assert "color" not in body


def test_delete_project(mock_client):
    mock_client.return_value = {}
    result = ticktick_delete_project("p1")
    mock_client.assert_called_once_with("DELETE", "/project/p1")
    assert result["success"] is True


def test_create_project_raises_tool_error(mock_client):
    mock_client.side_effect = RuntimeError("API error 403: Forbidden")
    with pytest.raises(ToolError):
        ticktick_create_project("Fail")
