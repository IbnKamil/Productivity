from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, Event


def record_event(db: Session, event_type: str, user_id: str | None, payload: dict | None = None) -> None:
    db.add(Event(event_type=event_type, user_id=user_id, payload=payload or {}))


def record_audit(
    db: Session,
    request: Request | None,
    action: str,
    user_id: str | None,
    metadata: dict | None = None,
) -> None:
    ip_address = request.client.host if request and request.client else None
    request_id = getattr(request.state, "request_id", None) if request else None
    db.add(
        AuditLog(
            action=action,
            user_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata_json=metadata or {},
        )
    )
