from productivity_mcp.providers.ticktick.schemas import (
    BulkTaskCreate,
    BulkTaskUpdate,
    Reminder,
    TaskItem,
    TaskRef,
)


def test_task_item_defaults():
    item = TaskItem(title="Buy milk")
    assert item.status == 0
    assert item.model_dump() == {"title": "Buy milk", "status": 0}


def test_reminder_dump():
    r = Reminder(trigger="TRIGGER:-PT15M")
    assert r.model_dump() == {"trigger": "TRIGGER:-PT15M"}


def test_task_ref_dump():
    ref = TaskRef(taskId="abc", projectId="xyz")
    assert ref.model_dump() == {"taskId": "abc", "projectId": "xyz"}


def test_bulk_task_create_exclude_none():
    t = BulkTaskCreate(title="Do laundry")
    assert t.model_dump(exclude_none=True) == {"title": "Do laundry"}


def test_bulk_task_create_full():
    item = TaskItem(title="Step 1")
    reminder = Reminder(trigger="TRIGGER:PT0S")
    t = BulkTaskCreate(
        title="Task",
        projectId="proj1",
        tags=["deepwork"],
        repeatFlag="RRULE:FREQ=DAILY",
        items=[item],
        reminders=[reminder],
    )
    dumped = t.model_dump(exclude_none=True)
    assert dumped["tags"] == ["deepwork"]
    assert dumped["repeatFlag"] == "RRULE:FREQ=DAILY"
    assert dumped["items"] == [{"title": "Step 1", "status": 0}]
    assert dumped["reminders"] == [{"trigger": "TRIGGER:PT0S"}]


def test_bulk_task_update_requires_ids():
    u = BulkTaskUpdate(taskId="t1", projectId="p1", title="Updated")
    assert u.model_dump(exclude_none=True) == {
        "taskId": "t1",
        "projectId": "p1",
        "title": "Updated",
    }
