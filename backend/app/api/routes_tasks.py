from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import envelope
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models import User
from app.services.audit import record_audit, record_event
from app.services.tasks import complete_task, current_task_payload, pause_task, skip_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/current")
def current_task(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return envelope(request, current_task_payload(db, user.id))


@router.post("/{task_id}/complete")
def complete(
    task_id: str,
    request: Request,
    _: None = Depends(rate_limit("tasks_complete")),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = complete_task(db, user, task_id)
    record_event(db, "task.completed", user.id, {"task_id": task_id})
    record_audit(db, request, "task.complete", user.id, {"task_id": task_id})
    db.commit()
    return envelope(request, result)


@router.post("/{task_id}/skip")
def skip(
    task_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = skip_task(db, user.id, task_id)
    record_audit(db, request, "task.skip", user.id, {"task_id": task_id})
    db.commit()
    return envelope(request, result)


@router.post("/{task_id}/pause")
def pause(
    task_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = pause_task(db, user.id, task_id)
    record_audit(db, request, "task.pause", user.id, {"task_id": task_id})
    db.commit()
    return envelope(request, result)
