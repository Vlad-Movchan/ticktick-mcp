# TickTick Feature Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add tags, recurring tasks, subtasks/checklist, reminders, project CRUD, and bulk operations to the TickTick MCP provider.

**Architecture:** Add a shared `schemas.py` with Pydantic models for nested inputs; extend existing `tasks.py` and `projects.py` with new optional fields/tools; add a new `bulk.py` for batch operations; mount the bulk sub-app in `__init__.py`. All features are direct TickTick Open API v1 passthroughs.

**Tech Stack:** Python 3.13, FastMCP, Pydantic v2, httpx, pytest, pytest-mock

---

## Task 0: Test infrastructure

**Files:**
- Install: `pytest-mock` dev dependency
- Create: `tests/__init__.py`
- Create: `tests/providers/__init__.py`
- Create: `tests/providers/ticktick/__init__.py`
- Create: `tests/providers/ticktick/tools/__init__.py`

**Step 1: Add pytest-mock**

```bash
uv add --dev pytest-mock
```

Expected: `pytest-mock` added to `[dependency-groups].dev` in `pyproject.toml`.

**Step 2: Create test directory structure**

```bash
mkdir -p tests/providers/ticktick/tools
touch tests/__init__.py tests/providers/__init__.py tests/providers/ticktick/__init__.py tests/providers/ticktick/tools/__init__.py
```

**Step 3: Verify pytest runs**

```bash
uv run pytest --collect-only
```

Expected: `no tests ran` with exit code 0 (collection succeeds, no errors).

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock tests/
git commit -m "chore: add test infrastructure and pytest-mock"
```

---

## Task 1: Pydantic schemas

**Files:**
- Create: `productivity_mcp/providers/ticktick/schemas.py`
- Create: `tests/providers/ticktick/test_schemas.py`

**Step 1: Write the failing test**

Create `tests/providers/ticktick/test_schemas.py`:

```python
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/providers/ticktick/test_schemas.py -v
```

Expected: `ImportError` — `schemas` module does not exist yet.

**Step 3: Create `schemas.py`**

Create `productivity_mcp/providers/ticktick/schemas.py`:

```python
from pydantic import BaseModel


class TaskItem(BaseModel):
    title: str
    status: int = 0  # 0=open, 1=completed


class Reminder(BaseModel):
    trigger: str  # ISO 8601 duration, e.g. "TRIGGER:-PT15M"


class TaskRef(BaseModel):
    taskId: str
    projectId: str


class BulkTaskCreate(BaseModel):
    title: str
    projectId: str | None = None
    content: str | None = None
    dueDate: str | None = None
    startDate: str | None = None
    priority: int | None = None
    tags: list[str] | None = None
    repeatFlag: str | None = None
    items: list[TaskItem] | None = None
    reminders: list[Reminder] | None = None


class BulkTaskUpdate(BaseModel):
    taskId: str
    projectId: str
    title: str | None = None
    content: str | None = None
    dueDate: str | None = None
    startDate: str | None = None
    priority: int | None = None
    tags: list[str] | None = None
    repeatFlag: str | None = None
    items: list[TaskItem] | None = None
    reminders: list[Reminder] | None = None
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/providers/ticktick/test_schemas.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add productivity_mcp/providers/ticktick/schemas.py tests/providers/ticktick/test_schemas.py
git commit -m "feat: add ticktick pydantic schemas"
```

---

## Task 2: Extend task tools (tags, repeatFlag, items, reminders)

**Files:**
- Modify: `productivity_mcp/providers/ticktick/tools/tasks.py`
- Create: `tests/providers/ticktick/tools/test_tasks.py`

**Step 1: Write failing tests**

Create `tests/providers/ticktick/tools/test_tasks.py`:

```python
from unittest.mock import MagicMock
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/providers/ticktick/tools/test_tasks.py -v
```

Expected: Multiple FAILs — new params don't exist yet, and startDate bug present.

**Step 3: Rewrite `tasks.py`**

Replace the entire contents of `productivity_mcp/providers/ticktick/tools/tasks.py`:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from productivity_mcp.providers.ticktick import client
from productivity_mcp.providers.ticktick.schemas import Reminder, TaskItem

mcp = FastMCP("tasks")


@mcp.tool
def ticktick_create_task(
    title: str,
    projectId: str | None = None,
    content: str | None = None,
    dueDate: str | None = None,
    startDate: str | None = None,
    priority: int | None = None,
    tags: list[str] | None = None,
    repeatFlag: str | None = None,
    items: list[TaskItem] | None = None,
    reminders: list[Reminder] | None = None,
) -> dict:
    """Create a new task in TickTick.

    Args:
        title: Task title.
        projectId: Project to add the task to (uses inbox if omitted).
        content: Task notes/description.
        startDate: Start date in ISO 8601 format (e.g. 2024-12-31T00:00:00+0000).
        dueDate: Due date in ISO 8601 format (e.g. 2024-12-31T00:00:00+0000).
        priority: Priority level: 0=none, 1=low, 3=medium, 5=high.
        tags: List of tag names (e.g. ["deepwork", "health"]).
        repeatFlag: Recurrence rule in RRULE format (e.g. "RRULE:FREQ=WEEKLY;BYDAY=TU,TH").
        items: Checklist items within the task.
        reminders: Reminders for the task (e.g. [{"trigger": "TRIGGER:-PT15M"}]).
    """
    body: dict = {"title": title}
    if projectId is not None:
        body["projectId"] = projectId
    if content is not None:
        body["content"] = content
    if startDate is not None:
        body["startDate"] = startDate
    if dueDate is not None:
        body["dueDate"] = dueDate
    if priority is not None:
        body["priority"] = priority
    if tags is not None:
        body["tags"] = tags
    if repeatFlag is not None:
        body["repeatFlag"] = repeatFlag
    if items is not None:
        body["items"] = [i.model_dump() for i in items]
    if reminders is not None:
        body["reminders"] = [r.model_dump() for r in reminders]

    try:
        task = client.request("POST", "/task", json=body)
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"id": task.get("id"), "title": task.get("title"), "projectId": task.get("projectId")}


@mcp.tool
def ticktick_get_task(projectId: str, taskId: str) -> dict:
    """Get full details for a specific task.

    Args:
        projectId: The project the task belongs to.
        taskId: The task ID.
    """
    try:
        return client.request("GET", f"/project/{projectId}/task/{taskId}")
    except RuntimeError as e:
        raise ToolError(str(e))


@mcp.tool
def ticktick_update_task(
    taskId: str,
    projectId: str,
    title: str | None = None,
    content: str | None = None,
    startDate: str | None = None,
    dueDate: str | None = None,
    priority: int | None = None,
    tags: list[str] | None = None,
    repeatFlag: str | None = None,
    items: list[TaskItem] | None = None,
    reminders: list[Reminder] | None = None,
) -> dict:
    """Update fields on an existing task.

    Args:
        taskId: The task ID to update.
        projectId: The project the task belongs to.
        title: New title.
        content: New notes/description.
        startDate: Start date in ISO 8601 format (e.g. 2024-12-31T00:00:00+0000).
        dueDate: New due date in ISO 8601 format.
        priority: New priority: 0=none, 1=low, 3=medium, 5=high.
        tags: Updated list of tag names.
        repeatFlag: Recurrence rule in RRULE format.
        items: Updated checklist items.
        reminders: Updated reminders.
    """
    body: dict = {"id": taskId, "projectId": projectId}
    if title is not None:
        body["title"] = title
    if content is not None:
        body["content"] = content
    if startDate is not None:
        body["startDate"] = startDate
    if dueDate is not None:
        body["dueDate"] = dueDate
    if priority is not None:
        body["priority"] = priority
    if tags is not None:
        body["tags"] = tags
    if repeatFlag is not None:
        body["repeatFlag"] = repeatFlag
    if items is not None:
        body["items"] = [i.model_dump() for i in items]
    if reminders is not None:
        body["reminders"] = [r.model_dump() for r in reminders]

    try:
        return client.request("POST", f"/task/{taskId}", json=body)
    except RuntimeError as e:
        raise ToolError(str(e))


@mcp.tool
def ticktick_complete_task(projectId: str, taskId: str) -> dict:
    """Mark a task as complete.

    Args:
        projectId: The project the task belongs to.
        taskId: The task ID to complete.
    """
    try:
        client.request("POST", f"/project/{projectId}/task/{taskId}/complete")
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "message": f"Task {taskId} marked as complete."}


@mcp.tool
def ticktick_delete_task(projectId: str, taskId: str) -> dict:
    """Delete a task.

    Args:
        projectId: The project the task belongs to.
        taskId: The task ID to delete.
    """
    try:
        client.request("DELETE", f"/project/{projectId}/task/{taskId}")
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "message": f"Task {taskId} deleted."}
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/providers/ticktick/tools/test_tasks.py -v
```

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add productivity_mcp/providers/ticktick/tools/tasks.py tests/providers/ticktick/tools/test_tasks.py
git commit -m "feat: extend create/update task with tags, recurrence, subtasks, reminders"
```

---

## Task 3: Project CRUD

**Files:**
- Modify: `productivity_mcp/providers/ticktick/tools/projects.py`
- Create: `tests/providers/ticktick/tools/test_projects.py`

**Step 1: Write failing tests**

Create `tests/providers/ticktick/tools/test_projects.py`:

```python
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/providers/ticktick/tools/test_projects.py -v
```

Expected: `ImportError` — new functions not yet defined.

**Step 3: Extend `projects.py`**

Replace the entire contents of `productivity_mcp/providers/ticktick/tools/projects.py`:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from productivity_mcp.providers.ticktick import client

mcp = FastMCP("projects")


@mcp.tool
def ticktick_list_projects() -> list[dict]:
    """List all TickTick projects."""
    try:
        projects = client.request("GET", "/project")
    except RuntimeError as e:
        raise ToolError(str(e))
    return [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "color": p.get("color"),
            "kind": p.get("kind"),
        }
        for p in projects
    ]


@mcp.tool
def ticktick_get_project_tasks(projectId: str) -> list[dict]:
    """Get all tasks for a TickTick project.

    Args:
        projectId: The project ID to retrieve tasks from.
    """
    try:
        data = client.request("GET", f"/project/{projectId}/data")
    except RuntimeError as e:
        raise ToolError(str(e))
    tasks = data.get("tasks", []) if isinstance(data, dict) else data
    return [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "due_date": t.get("dueDate"),
        }
        for t in tasks
    ]


@mcp.tool
def ticktick_create_project(
    name: str,
    color: str | None = None,
    kind: str | None = None,
) -> dict:
    """Create a new TickTick project.

    Args:
        name: Project name.
        color: Hex color string (e.g. "#ff0000").
        kind: Project type: "TASK" (default) or "NOTE".
    """
    body: dict = {"name": name}
    if color is not None:
        body["color"] = color
    if kind is not None:
        body["kind"] = kind
    try:
        project = client.request("POST", "/project", json=body)
    except RuntimeError as e:
        raise ToolError(str(e))
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "color": project.get("color"),
        "kind": project.get("kind"),
    }


@mcp.tool
def ticktick_update_project(
    projectId: str,
    name: str | None = None,
    color: str | None = None,
) -> dict:
    """Update a TickTick project.

    Args:
        projectId: The project ID to update.
        name: New project name.
        color: New hex color string (e.g. "#ff0000").
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if color is not None:
        body["color"] = color
    try:
        project = client.request("PUT", f"/project/{projectId}", json=body)
    except RuntimeError as e:
        raise ToolError(str(e))
    return {
        "id": project.get("id"),
        "name": project.get("name"),
        "color": project.get("color"),
        "kind": project.get("kind"),
    }


@mcp.tool
def ticktick_delete_project(projectId: str) -> dict:
    """Delete a TickTick project.

    Args:
        projectId: The project ID to delete.
    """
    try:
        client.request("DELETE", f"/project/{projectId}")
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "message": f"Project {projectId} deleted."}
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/providers/ticktick/tools/test_projects.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add productivity_mcp/providers/ticktick/tools/projects.py tests/providers/ticktick/tools/test_projects.py
git commit -m "feat: add project create, update, delete tools"
```

---

## Task 4: Bulk operations

**Files:**
- Create: `productivity_mcp/providers/ticktick/tools/bulk.py`
- Create: `tests/providers/ticktick/tools/test_bulk.py`

**Step 1: Write failing tests**

Create `tests/providers/ticktick/tools/test_bulk.py`:

```python
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
```

**Step 2: Run to verify failure**

```bash
uv run pytest tests/providers/ticktick/tools/test_bulk.py -v
```

Expected: `ImportError` — `bulk.py` does not exist yet.

**Step 3: Create `bulk.py`**

Create `productivity_mcp/providers/ticktick/tools/bulk.py`:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from productivity_mcp.providers.ticktick import client
from productivity_mcp.providers.ticktick.schemas import BulkTaskCreate, BulkTaskUpdate, TaskRef

mcp = FastMCP("bulk")


@mcp.tool
def ticktick_bulk_create_tasks(tasks: list[BulkTaskCreate]) -> dict:
    """Create multiple tasks in one request.

    Args:
        tasks: List of tasks to create. Each task supports the same fields as ticktick_create_task.
    """
    payload = [t.model_dump(exclude_none=True) for t in tasks]
    try:
        client.request("POST", "/batch/task", json={"add": payload})
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "count": len(tasks)}


@mcp.tool
def ticktick_bulk_update_tasks(tasks: list[BulkTaskUpdate]) -> dict:
    """Update multiple tasks in one request.

    Args:
        tasks: List of tasks to update. taskId and projectId are required for each.
    """
    payload = [t.model_dump(exclude_none=True) for t in tasks]
    try:
        client.request("POST", "/batch/task", json={"update": payload})
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "count": len(tasks)}


@mcp.tool
def ticktick_bulk_complete_tasks(tasks: list[TaskRef]) -> dict:
    """Mark multiple tasks as complete.

    Args:
        tasks: List of task references (taskId + projectId) to complete.
    """
    try:
        for ref in tasks:
            client.request("POST", f"/project/{ref.projectId}/task/{ref.taskId}/complete")
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "count": len(tasks)}


@mcp.tool
def ticktick_bulk_delete_tasks(tasks: list[TaskRef]) -> dict:
    """Delete multiple tasks in one request.

    Args:
        tasks: List of task references (taskId + projectId) to delete.
    """
    payload = [t.model_dump() for t in tasks]
    try:
        client.request("POST", "/batch/task", json={"delete": payload})
    except RuntimeError as e:
        raise ToolError(str(e))
    return {"success": True, "count": len(tasks)}
```

**Step 4: Run tests to verify pass**

```bash
uv run pytest tests/providers/ticktick/tools/test_bulk.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add productivity_mcp/providers/ticktick/tools/bulk.py tests/providers/ticktick/tools/test_bulk.py
git commit -m "feat: add bulk create, update, complete, delete task tools"
```

---

## Task 5: Wire up bulk tools and run full test suite

**Files:**
- Modify: `productivity_mcp/providers/ticktick/__init__.py`

**Step 1: Mount bulk sub-app**

Edit `productivity_mcp/providers/ticktick/__init__.py`. Change:

```python
from productivity_mcp.providers.ticktick.tools import auth_tools, projects, tasks
```

to:

```python
from productivity_mcp.providers.ticktick.tools import auth_tools, bulk, projects, tasks
```

And add `mcp.mount(bulk.mcp)` inside `register()`:

```python
def register(mcp: FastMCP) -> None:
    mcp.mount(auth_tools.mcp)
    mcp.mount(tasks.mcp)
    mcp.mount(projects.mcp)
    mcp.mount(bulk.mcp)
```

**Step 2: Run the full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASS (Task 0–4 total).

**Step 3: Verify server starts without errors**

```bash
uv run productivity-mcp &
sleep 2
curl -s http://localhost:8000/mcp | head -c 200
kill %1
```

Expected: Server starts, `/mcp` endpoint responds (may return 400/405 without a proper MCP handshake, but no import errors).

**Step 4: Commit**

```bash
git add productivity_mcp/providers/ticktick/__init__.py
git commit -m "feat: mount bulk tools in ticktick provider"
```

---

## Final Checklist

- [ ] `pytest-mock` installed
- [ ] `schemas.py` created with 5 Pydantic models
- [ ] `tasks.py` extended with tags, repeatFlag, items, reminders (+ startDate bug fixed)
- [ ] `projects.py` extended with create, update, delete
- [ ] `bulk.py` created with 4 bulk tools
- [ ] `__init__.py` mounts bulk sub-app
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Server starts cleanly: `uv run productivity-mcp`
