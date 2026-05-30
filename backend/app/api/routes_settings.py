from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.utils import envelope
from app.core.database import get_db
from app.models import Settings, User
from app.schemas.settings import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_out(settings: Settings) -> SettingsOut:
    return SettingsOut(
        energy_mode=settings.energy_mode,
        task_density=settings.task_density,
        notifications_enabled=settings.notifications_enabled,
        sounds_enabled=settings.sounds_enabled,
        theme=settings.theme,
    )


def _get_settings(db: Session, user_id: str) -> Settings:
    settings = db.scalar(select(Settings).where(Settings.user_id == user_id))
    if settings:
        return settings
    settings = Settings(user_id=user_id)
    db.add(settings)
    db.flush()
    return settings


@router.get("")
def get_user_settings(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = _get_settings(db, user.id)
    db.commit()
    return envelope(request, _settings_out(settings))


@router.patch("")
def update_user_settings(
    payload: SettingsUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = _get_settings(db, user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return envelope(request, _settings_out(settings))
