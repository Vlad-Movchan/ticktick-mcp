import pytest
from fastmcp.exceptions import ToolError
from productivity_mcp.providers.ticktick.schemas import BulkTaskCreate, BulkTaskUpdate, TaskRef
from productivity_mcp.providers.ticktick.tools.bulk import (
    ticktick_bulk_complete_tasks,
    ticktick_bulk_create_tasks,
    ticktick_bulk_delete_tasks,
    ticktick_bulk_update_tasks,
)


@pytest.fixture
def mock_client(mocker):
    return mocker.patch("productivity_mcp.providers.ticktick.tools.bulk.client.request")


def test_bulk_create_sends_add_payload(mock_client):
    mock_client.return_value = {"id2Tasks": {}}
    tasks = [BulkTaskCreate(title="Task A"), BulkTaskCreate(title="Task B", projectId="p1")]
    result = ticktick_bulk_create_tasks(tasks)
    mock_client.assert_called_once()
    args, kwargs = mock_client.call_args
    assert args == ("POST", "/batch/task")
    assert kwargs["json"]["add"] == [
        {"title": "Task A"},
        {"title": "Task B", "projectId": "p1"},
    ]
    assert result["success"] is True
    assert result["count"] == 2


def test_bulk_update_sends_update_payload(mock_client):
    mock_client.return_value = {}
    tasks = [BulkTaskUpdate(taskId="t1", projectId="p1", title="Updated")]
    ticktick_bulk_update_tasks(tasks)
    body = mock_client.call_args[1]["json"]
    assert body["update"] == [{"taskId": "t1", "projectId": "p1", "title": "Updated"}]


def test_bulk_delete_sends_delete_payload(mock_client):
    mock_client.return_value = {}
    refs = [TaskRef(taskId="t1", projectId="p1"), TaskRef(taskId="t2", projectId="p1")]
    result = ticktick_bulk_delete_tasks(refs)
    body = mock_client.call_args[1]["json"]
    assert body["delete"] == [
        {"taskId": "t1", "projectId": "p1"},
        {"taskId": "t2", "projectId": "p1"},
    ]
    assert result["count"] == 2


def test_bulk_complete_calls_complete_per_task(mock_client):
    mock_client.return_value = {}
    refs = [TaskRef(taskId="t1", projectId="p1"), TaskRef(taskId="t2", projectId="p2")]
    result = ticktick_bulk_complete_tasks(refs)
    assert mock_client.call_count == 2
    mock_client.assert_any_call("POST", "/project/p1/task/t1/complete")
    mock_client.assert_any_call("POST", "/project/p2/task/t2/complete")
    assert result["count"] == 2


def test_bulk_create_raises_tool_error(mock_client):
    mock_client.side_effect = RuntimeError("API error 500")
    with pytest.raises(ToolError):
        ticktick_bulk_create_tasks([BulkTaskCreate(title="Fail")])


def test_bulk_complete_raises_tool_error_on_first_failure(mock_client):
    mock_client.side_effect = RuntimeError("API error 404")
    with pytest.raises(ToolError):
        ticktick_bulk_complete_tasks([TaskRef(taskId="t1", projectId="p1")])
