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
