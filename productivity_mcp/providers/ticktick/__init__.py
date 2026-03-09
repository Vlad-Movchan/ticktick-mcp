from fastmcp import FastMCP

from productivity_mcp.providers.ticktick.tools import auth_tools, bulk, projects, tasks

REQUIRED_ENV_VARS = ["TICKTICK_CLIENT_ID", "TICKTICK_CLIENT_SECRET"]


def register(mcp: FastMCP) -> None:
    mcp.mount(auth_tools.mcp)
    mcp.mount(tasks.mcp)
    mcp.mount(projects.mcp)
    mcp.mount(bulk.mcp)
