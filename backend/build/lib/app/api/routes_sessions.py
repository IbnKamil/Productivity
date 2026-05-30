from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import envelope
from app.core.database import get_db
from app.models import User
from app.services.audit import record_audit
from app.services.tasks import current_session, end_session, start_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start")
def start(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = start_session(db, user.id)
    record_audit(db, request, "session.start", user.id)
    db.commit()
    return envelope(request, result)


@router.post("/end")
def end(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = end_session(db, user.id)
    record_audit(db, request, "session.end", user.id)
    db.commit()
    return envelope(request, result)


@router.get("/current")
def current(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return envelope(request, current_session(db, user.id))
