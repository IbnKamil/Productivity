from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    energy_mode: str
    task_density: str
    notifications_enabled: bool
    sounds_enabled: bool
    theme: str


class SettingsUpdate(BaseModel):
    energy_mode: str | None = Field(default=None, pattern="^(low|normal|high)$")
    task_density: str | None = Field(default=None, pattern="^(light|balanced|dense)$")
    notifications_enabled: bool | None = None
    sounds_enabled: bool | None = None
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
