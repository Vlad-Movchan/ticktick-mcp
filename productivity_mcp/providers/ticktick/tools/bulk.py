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
