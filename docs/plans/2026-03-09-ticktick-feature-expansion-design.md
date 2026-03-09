# TickTick Feature Expansion — Design

**Date:** 2026-03-09
**Scope:** 6 new features added to the TickTick provider

---

## Overview

Extend the existing TickTick MCP integration with tags, recurring tasks, subtasks/checklist, reminders, project CRUD, and bulk operations. All features use the TickTick Open API v1. No client-side aggregation required — every feature is a direct API passthrough.

---

## New Pydantic Schemas (`schemas.py`)

A new `productivity_mcp/providers/ticktick/schemas.py` module centralizes all shared input models.

| Model | Fields | Purpose |
|---|---|---|
| `TaskItem` | `title: str`, `status: int = 0` | Checklist item within a task |
| `Reminder` | `trigger: str` | ISO 8601 duration, e.g. `TRIGGER:-PT15M` |
| `TaskRef` | `taskId: str`, `projectId: str` | Identifies a task for bulk complete/delete |
| `BulkTaskCreate` | All `create_task` fields | Payload item for bulk create |
| `BulkTaskUpdate` | All `update_task` fields (`taskId`+`projectId` required) | Payload item for bulk update |

All models use `model_dump(exclude_none=True)` when building API request bodies.

---

## Extended Task Tools (`tasks.py`)

`ticktick_create_task` and `ticktick_update_task` gain four new optional parameters:

| Param | Type | Notes |
|---|---|---|
| `tags` | `list[str] \| None` | e.g. `["deepwork", "health"]` |
| `repeatFlag` | `str \| None` | Raw RRULE, e.g. `RRULE:FREQ=WEEKLY;BYDAY=TU,TH` |
| `items` | `list[TaskItem] \| None` | Ordered checklist items |
| `reminders` | `list[Reminder] \| None` | Reminder triggers |

Serialization: `items` and `reminders` are serialized via `.model_dump()` before inclusion in the request body.

---

## Extended Project Tools (`projects.py`)

Three new tools added alongside the existing `list` and `get_tasks`:

| Tool | Method | Endpoint | Key params |
|---|---|---|---|
| `ticktick_create_project` | POST | `/project` | `name`, `color?`, `kind?` |
| `ticktick_update_project` | PUT | `/project/{projectId}` | `projectId`, `name?`, `color?` |
| `ticktick_delete_project` | DELETE | `/project/{projectId}` | `projectId` |

`kind` accepts `TASK` or `NOTE` (TickTick project types).

---

## Bulk Operations (`bulk.py`)

New file with 4 tools. All call the `/batch/task` endpoint with a single request body containing `add`, `update`, `delete` arrays as needed. Complete uses `/project/{projectId}/task/{taskId}/complete` per task (TickTick has no batch complete endpoint).

| Tool | Input | API |
|---|---|---|
| `ticktick_bulk_create_tasks` | `list[BulkTaskCreate]` | `POST /batch/task` → `{add: [...]}` |
| `ticktick_bulk_update_tasks` | `list[BulkTaskUpdate]` | `POST /batch/task` → `{update: [...]}` |
| `ticktick_bulk_complete_tasks` | `list[TaskRef]` | `POST /project/{id}/task/{id}/complete` × N |
| `ticktick_bulk_delete_tasks` | `list[TaskRef]` | `POST /batch/task` → `{delete: [...]}` |

`bulk_complete_tasks` issues N requests (one per task). This is acceptable — bulk complete is rare and TickTick provides no batch endpoint for it.

---

## File Changes Summary

| File | Change |
|---|---|
| `providers/ticktick/schemas.py` | **New** — `TaskItem`, `Reminder`, `TaskRef`, `BulkTaskCreate`, `BulkTaskUpdate` |
| `providers/ticktick/tools/tasks.py` | **Extend** — add `tags`, `repeatFlag`, `items`, `reminders` to create + update |
| `providers/ticktick/tools/projects.py` | **Extend** — add `create`, `update`, `delete` tools |
| `providers/ticktick/tools/bulk.py` | **New** — 4 bulk tools |
| `providers/ticktick/tools/__init__.py` | **Update** — register bulk sub-app |
| `providers/ticktick/__init__.py` | **Update** — mount bulk tools if needed |

---

## Error Handling

No change to the existing pattern: all `RuntimeError` from `client.request` are re-raised as `ToolError`. Bulk operations catch errors per-item and surface the first failure (fail-fast).

---

## Out of Scope

- Filter tasks by date (removed — requires N+1 across all projects)
- Natural language recurrence parsing
- TickTick unofficial/v2 API
