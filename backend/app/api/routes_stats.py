from sqlalchemy import Date, cast, func, select
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import envelope
from app.core.database import get_db
from app.models import Goal, GoalStatus, TaskCompletion, User, UserStats
from app.schemas.stats import HistoryPoint, StatsSummary
from app.services.tasks import ensure_user_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def summary(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stats = ensure_user_stats(db, user.id)
    active_goals = (
        db.scalar(select(func.count(Goal.id)).where(Goal.user_id == user.id, Goal.status == GoalStatus.active))
        or 0
    )
    db.commit()
    return envelope(
        request,
        StatsSummary(
            completed_tasks=stats.completed_tasks,
            completed_goals=stats.completed_goals,
            reward_points=stats.reward_points,
            streak_days=stats.streak_days,
            total_focus_seconds=stats.total_focus_seconds,
            active_goals=active_goals,
        ),
    )


@router.get("/history")
def history(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            cast(TaskCompletion.completed_at, Date).label("day"),
            func.count(TaskCompletion.id),
            func.coalesce(func.sum(TaskCompletion.reward_points), 0),
        )
        .where(TaskCompletion.user_id == user.id)
        .group_by("day")
        .order_by("day")
    ).all()
    points = [
        HistoryPoint(day=row[0], completed_tasks=row[1], reward_points=row[2])
        for row in rows
    ]
    return envelope(request, points)
