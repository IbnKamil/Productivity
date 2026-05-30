from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import envelope
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models import Goal, GoalStatus, TaskCompletion, User
from app.schemas.goals import GoalCreate, GoalDetail, GoalOut, GoalUpdate
from app.services.audit import record_audit, record_event
from app.services.tasks import generate_for_goal, goal_progress

router = APIRouter(prefix="/goals", tags=["goals"])


def _goal_out(db: Session, goal: Goal) -> GoalOut:
    completed, total, percent = goal_progress(db, goal.id)
    return GoalOut(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        priority=goal.priority,
        due_date=goal.due_date,
        complexity=goal.complexity,
        context=goal.context,
        status=goal.status.value if hasattr(goal.status, "value") else str(goal.status),
        completed_tasks=completed,
        total_tasks=total,
        progress_percent=percent,
        created_at=goal.created_at,
        completed_at=goal.completed_at,
    )


def _owned_goal(db: Session, user_id: str, goal_id: str) -> Goal:
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return goal


@router.post("")
def create_goal(
    payload: GoalCreate,
    request: Request,
    _: None = Depends(rate_limit("goals_create")),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = Goal(user_id=user.id, **payload.model_dump())
    db.add(goal)
    db.flush()
    generated = generate_for_goal(db, goal)
    record_event(db, "goal.created", user.id, {"goal_id": goal.id})
    record_audit(db, request, "goal.create", user.id, {"goal_id": goal.id})
    db.commit()
    db.refresh(goal)
    return envelope(
        request,
        {
            "goal": _goal_out(db, goal),
            "generated": generated,
        },
    )


@router.get("")
def list_goals(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = db.scalars(
        select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc())
    ).all()
    return envelope(request, [_goal_out(db, goal) for goal in goals])


@router.get("/{goal_id}")
def get_goal(
    goal_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = _owned_goal(db, user.id, goal_id)
    history = db.scalars(
        select(TaskCompletion)
        .where(TaskCompletion.user_id == user.id, TaskCompletion.goal_id == goal.id)
        .order_by(TaskCompletion.completed_at.desc())
        .limit(50)
    ).all()
    base = _goal_out(db, goal).model_dump()
    return envelope(
        request,
        GoalDetail(
            **base,
            completed_history=[
                {
                    "task_id": item.task_id,
                    "completed_at": item.completed_at,
                    "reward_points": item.reward_points,
                }
                for item in history
            ],
        ),
    )


@router.patch("/{goal_id}")
def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = _owned_goal(db, user.id, goal_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] is not None:
        values["status"] = GoalStatus(values["status"])
    for key, value in values.items():
        setattr(goal, key, value)
    record_audit(db, request, "goal.update", user.id, {"goal_id": goal.id})
    db.commit()
    db.refresh(goal)
    return envelope(request, _goal_out(db, goal))


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = _owned_goal(db, user.id, goal_id)
    db.delete(goal)
    record_audit(db, request, "goal.delete", user.id, {"goal_id": goal_id})
    db.commit()
    return envelope(request, {"deleted": True})


@router.post("/{goal_id}/generate")
def generate_goal_tasks(
    goal_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = _owned_goal(db, user.id, goal_id)
    result = generate_for_goal(db, goal)
    record_audit(db, request, "goal.generate_tasks", user.id, {"goal_id": goal.id})
    db.commit()
    return envelope(request, result)
