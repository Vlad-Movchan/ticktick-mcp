import pytest
from productivity_mcp.providers.ticktick.schemas import Reminder, TaskItem
from productivity_mcp.providers.ticktick.tools.tasks import (
    ticktick_create_task,
    ticktick_update_task,
)


@pytest.fixture
def mock_client(mocker):
    return mocker.patch("productivity_mcp.providers.ticktick.tools.tasks.client.request")


def test_create_task_sends_tags(mock_client):
    mock_client.return_value = {"id": "1", "title": "Test", "projectId": "p1"}
    ticktick_create_task("Test", projectId="p1", tags=["deepwork", "health"])
    body = mock_client.call_args[1]["json"]
    assert body["tags"] == ["deepwork", "health"]


def test_create_task_sends_repeat_flag(mock_client):
    mock_client.return_value = {"id": "1", "title": "Training", "projectId": None}
    ticktick_create_task("Training", repeatFlag="RRULE:FREQ=WEEKLY;BYDAY=TU,TH")
    body = mock_client.call_args[1]["json"]
    assert body["repeatFlag"] == "RRULE:FREQ=WEEKLY;BYDAY=TU,TH"


def test_create_task_sends_items(mock_client):
    mock_client.return_value = {"id": "1", "title": "Grocery", "projectId": None}
    items = [TaskItem(title="Milk"), TaskItem(title="Eggs", status=1)]
    ticktick_create_task("Grocery", items=items)
    body = mock_client.call_args[1]["json"]
    assert body["items"] == [{"title": "Milk", "status": 0}, {"title": "Eggs", "status": 1}]


def test_create_task_sends_reminders(mock_client):
    mock_client.return_value = {"id": "1", "title": "Meeting", "projectId": None}
    reminders = [Reminder(trigger="TRIGGER:-PT15M")]
    ticktick_create_task("Meeting", reminders=reminders)
    body = mock_client.call_args[1]["json"]
    assert body["reminders"] == [{"trigger": "TRIGGER:-PT15M"}]


def test_create_task_omits_none_fields(mock_client):
    mock_client.return_value = {"id": "1", "title": "Bare", "projectId": None}
    ticktick_create_task("Bare")
    body = mock_client.call_args[1]["json"]
    assert "tags" not in body
    assert "repeatFlag" not in body
    assert "items" not in body
    assert "reminders" not in body


def test_update_task_sends_tags(mock_client):
    mock_client.return_value = {"id": "1"}
    ticktick_update_task("t1", "p1", tags=["focus"])
    body = mock_client.call_args[1]["json"]
    assert body["tags"] == ["focus"]


def test_update_task_startdate_bug_fixed(mock_client):
    """startDate was incorrectly set to dueDate value — ensure it's fixed."""
    mock_client.return_value = {"id": "1"}
    ticktick_update_task("t1", "p1", startDate="2026-01-01T00:00:00+0000", dueDate="2026-02-01T00:00:00+0000")
    body = mock_client.call_args[1]["json"]
    assert body["startDate"] == "2026-01-01T00:00:00+0000"
    assert body["dueDate"] == "2026-02-01T00:00:00+0000"
