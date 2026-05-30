from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.redis import cache
from app.models import (
    Goal,
    GoalStatus,
    MicroTask,
    SessionStatus,
    TaskCompletion,
    TaskSession,
    TaskStatus,
    User,
    UserStats,
)
from app.schemas.tasks import CompletionOut, CurrentTaskOut, GenerateTasksOut, MicroTaskOut, SessionOut
from app.services.decomposer import TaskDecomposer


def task_to_schema(task: MicroTask, goal_title: str | None = None) -> MicroTaskOut:
    return MicroTaskOut(
        id=task.id,
        goal_id=task.goal_id,
        goal_title=goal_title or (task.goal.title if task.goal else None),
        title=task.title,
        description=task.description,
        estimated_seconds=task.estimated_seconds,
        difficulty_score=task.difficulty_score,
        value_score=task.value_score,
        clarity_score=task.clarity_score,
        energy_fit_score=task.energy_fit_score,
        momentum_score=task.momentum_score,
        status=task.status.value if hasattr(task.status, "value") else str(task.status),
        order_index=task.order_index,
    )


def goal_progress(db: Session, goal_id: str) -> tuple[int, int, int]:
    total = db.scalar(select(func.count(MicroTask.id)).where(MicroTask.goal_id == goal_id)) or 0
    completed = (
        db.scalar(
            select(func.count(MicroTask.id)).where(
                MicroTask.goal_id == goal_id, MicroTask.status == TaskStatus.completed
            )
        )
        or 0
    )
    percent = int((completed / total) * 100) if total else 0
    return completed, total, percent


def ensure_user_stats(db: Session, user_id: str) -> UserStats:
    stats = db.scalar(select(UserStats).where(UserStats.user_id == user_id))
    if stats:
        return stats
    stats = UserStats(user_id=user_id)
    db.add(stats)
    db.flush()
    return stats


def generate_for_goal(db: Session, goal: Goal) -> GenerateTasksOut:
    existing = db.scalar(select(func.count(MicroTask.id)).where(MicroTask.goal_id == goal.id)) or 0
    if existing:
        current = get_or_select_current_task(db, goal.user_id, goal.id)
        return GenerateTasksOut(
            goal_id=goal.id,
            generated_count=0,
            current_task=task_to_schema(current, goal.title) if current else None,
        )

    decomposer = TaskDecomposer()
    generated = decomposer.decompose(goal.title, goal.description, goal.complexity, goal.context)
    tasks = [
        MicroTask(
            goal_id=goal.id,
            user_id=goal.user_id,
            title=item.title,
            description=item.description,
            estimated_seconds=item.estimated_seconds,
            difficulty_score=item.difficulty_score,
            value_score=item.value_score,
            clarity_score=item.clarity_score,
            energy_fit_score=item.energy_fit_score,
            momentum_score=item.momentum_score,
            order_index=item.order_index,
            status=TaskStatus.current if item.order_index == 0 else TaskStatus.pending,
        )
        for item in generated
    ]
    db.add_all(tasks)
    db.flush()
    goal.current_task_id = tasks[0].id if tasks else None
    cache.delete(f"current-task:{goal.user_id}")
    return GenerateTasksOut(
        goal_id=goal.id,
        generated_count=len(tasks),
        current_task=task_to_schema(tasks[0], goal.title) if tasks else None,
    )


def get_or_select_current_task(db: Session, user_id: str, goal_id: str | None = None) -> MicroTask | None:
    query = (
        select(MicroTask)
        .join(Goal, Goal.id == MicroTask.goal_id)
        .where(MicroTask.user_id == user_id, Goal.status == GoalStatus.active)
    )
    if goal_id:
        query = query.where(MicroTask.goal_id == goal_id)
    current = db.scalar(
        query.where(MicroTask.status == TaskStatus.current).order_by(Goal.created_at, MicroTask.order_index)
    )
    if current:
        return current
    pending = db.scalar(
        query.where(MicroTask.status == TaskStatus.pending).order_by(Goal.created_at, MicroTask.order_index)
    )
    if pending:
        pending.status = TaskStatus.current
        pending.goal.current_task_id = pending.id
        db.flush()
    return pending


def current_task_payload(db: Session, user_id: str) -> CurrentTaskOut:
    cached = cache.get_json(f"current-task:{user_id}")
    if cached:
        return CurrentTaskOut(**cached)

    task = get_or_select_current_task(db, user_id)
    if not task:
        payload = CurrentTaskOut(
            task=None,
            goal=None,
            progress_percent=0,
            message="Создайте цель, чтобы открыть первую маленькую задачу.",
        )
        cache.set_json(f"current-task:{user_id}", payload.model_dump(), 20)
        return payload

    completed, total, percent = goal_progress(db, task.goal_id)
    payload = CurrentTaskOut(
        task=task_to_schema(task, task.goal.title),
        goal={
            "id": task.goal.id,
            "title": task.goal.title,
            "completed_tasks": completed,
            "total_tasks": total,
        },
        progress_percent=percent,
        message="Виден только этот шаг. Завершите его, чтобы открыть следующий.",
    )
    cache.set_json(f"current-task:{user_id}", payload.model_dump(), 20)
    return payload


def complete_task(db: Session, user: User, task_id: str) -> CompletionOut:
    task = db.get(MicroTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задача не найдена")
    if task.status not in {TaskStatus.current, TaskStatus.completed}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Можно завершить только текущую видимую задачу")

    existing = db.scalar(
        select(TaskCompletion).where(
            TaskCompletion.user_id == user.id, TaskCompletion.task_id == task.id
        )
    )
    if existing:
        next_task = get_or_select_current_task(db, user.id, task.goal_id)
        _, _, percent = goal_progress(db, task.goal_id)
        return CompletionOut(
            completed_task_id=task.id,
            reward_points=existing.reward_points,
            progress_percent=percent,
            next_task=task_to_schema(next_task, next_task.goal.title) if next_task else None,
        )

    now = datetime.now(UTC)
    reward = 10 + task.value_score + task.momentum_score
    completion = TaskCompletion(
        user_id=user.id,
        task_id=task.id,
        goal_id=task.goal_id,
        reward_points=reward,
        completed_at=now,
    )
    db.add(completion)
    task.status = TaskStatus.completed
    task.completed_at = now

    stats = ensure_user_stats(db, user.id)
    today = now.date()
    if stats.last_completion_date == today:
        pass
    elif stats.last_completion_date == today - timedelta(days=1):
        stats.streak_days += 1
    else:
        stats.streak_days = 1
    stats.last_completion_date = today
    stats.completed_tasks += 1
    stats.reward_points += reward
    stats.total_focus_seconds += task.estimated_seconds

    next_task = db.scalar(
        select(MicroTask)
        .where(
            MicroTask.goal_id == task.goal_id,
            MicroTask.user_id == user.id,
            MicroTask.status == TaskStatus.pending,
            MicroTask.order_index > task.order_index,
        )
        .order_by(MicroTask.order_index)
    )
    if next_task:
        next_task.status = TaskStatus.current
        task.goal.current_task_id = next_task.id
    else:
        task.goal.status = GoalStatus.completed
        task.goal.completed_at = now
        task.goal.current_task_id = None
        stats.completed_goals += 1

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return complete_task(db, user, task_id)

    cache.delete(f"current-task:{user.id}")
    _, _, percent = goal_progress(db, task.goal_id)
    return CompletionOut(
        completed_task_id=task.id,
        reward_points=reward,
        progress_percent=percent,
        next_task=task_to_schema(next_task, task.goal.title) if next_task else None,
    )


def skip_task(db: Session, user_id: str, task_id: str) -> CurrentTaskOut:
    task = db.get(MicroTask, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задача не найдена")
    if task.status != TaskStatus.current:
        raise HTTPException(status.HTTP_409_CONFLICT, "Можно пропустить только текущую задачу")
    task.status = TaskStatus.skipped
    next_task = get_or_select_current_task(db, user_id, task.goal_id)
    task.goal.current_task_id = next_task.id if next_task else None
    cache.delete(f"current-task:{user_id}")
    return current_task_payload(db, user_id)


def pause_task(db: Session, user_id: str, task_id: str) -> CurrentTaskOut:
    task = db.get(MicroTask, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Задача не найдена")
    if task.status == TaskStatus.current:
        task.status = TaskStatus.paused
        task.goal.status = GoalStatus.paused
    cache.delete(f"current-task:{user_id}")
    return CurrentTaskOut(
        task=task_to_schema(task, task.goal.title),
        goal={"id": task.goal.id, "title": task.goal.title},
        progress_percent=goal_progress(db, task.goal_id)[2],
        message="Сессия приостановлена. Вернитесь, когда будете готовы.",
    )


def start_session(db: Session, user_id: str) -> SessionOut:
    task = get_or_select_current_task(db, user_id)
    session = TaskSession(
        user_id=user_id,
        goal_id=task.goal_id if task else None,
        current_task_id=task.id if task else None,
    )
    db.add(session)
    db.flush()
    return session_to_schema(session)


def current_session(db: Session, user_id: str) -> SessionOut | None:
    session = db.scalar(
        select(TaskSession)
        .where(TaskSession.user_id == user_id, TaskSession.status == SessionStatus.active)
        .order_by(TaskSession.started_at.desc())
    )
    return session_to_schema(session) if session else None


def end_session(db: Session, user_id: str) -> SessionOut:
    session = db.scalar(
        select(TaskSession)
        .where(TaskSession.user_id == user_id, TaskSession.status == SessionStatus.active)
        .order_by(TaskSession.started_at.desc())
    )
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Активная сессия не найдена")
    session.status = SessionStatus.ended
    session.ended_at = datetime.now(UTC)
    db.flush()
    return session_to_schema(session)


def session_to_schema(session: TaskSession) -> SessionOut:
    return SessionOut(
        id=session.id,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        goal_id=session.goal_id,
        current_task_id=session.current_task_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
    )
