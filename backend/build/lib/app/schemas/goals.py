from datetime import date, datetime

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    priority: int = Field(default=3, ge=1, le=5)
    due_date: date | None = None
    complexity: int = Field(default=3, ge=1, le=5)
    context: str | None = Field(default=None, max_length=2000)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None
    complexity: int | None = Field(default=None, ge=1, le=5)
    context: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|paused|completed|archived)$")


class GoalOut(BaseModel):
    id: str
    title: str
    description: str | None
    priority: int
    due_date: date | None
    complexity: int
    context: str | None
    status: str
    completed_tasks: int = 0
    total_tasks: int = 0
    progress_percent: int = 0
    created_at: datetime
    completed_at: datetime | None


class GoalDetail(GoalOut):
    completed_history: list[dict]
