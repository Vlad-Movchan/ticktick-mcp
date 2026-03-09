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
