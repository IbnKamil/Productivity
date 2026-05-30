from datetime import date

from pydantic import BaseModel


class StatsSummary(BaseModel):
    completed_tasks: int
    completed_goals: int
    reward_points: int
    streak_days: int
    total_focus_seconds: int
    active_goals: int


class HistoryPoint(BaseModel):
    day: date
    completed_tasks: int
    reward_points: int
