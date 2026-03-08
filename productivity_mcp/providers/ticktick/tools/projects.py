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
