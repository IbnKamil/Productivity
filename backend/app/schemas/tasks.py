from datetime import datetime

from pydantic import BaseModel, Field


class MicroTaskOut(BaseModel):
    id: str
    goal_id: str
    goal_title: str | None = None
    title: str
    description: str
    estimated_seconds: int
    difficulty_score: int
    value_score: int
    clarity_score: int
    energy_fit_score: int
    momentum_score: int
    status: str
    order_index: int


class CurrentTaskOut(BaseModel):
    task: MicroTaskOut | None
    goal: dict | None
    progress_percent: int
    message: str


class CompletionOut(BaseModel):
    completed_task_id: str
    reward_points: int
    progress_percent: int
    next_task: MicroTaskOut | None
    confirmation: str = "Step completed. Momentum increased."


class GenerateTasksOut(BaseModel):
    goal_id: str
    generated_count: int = Field(ge=0)
    current_task: MicroTaskOut | None


class SessionOut(BaseModel):
    id: str
    status: str
    goal_id: str | None
    current_task_id: str | None
    started_at: datetime
    ended_at: datetime | None
