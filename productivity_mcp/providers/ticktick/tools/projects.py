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
