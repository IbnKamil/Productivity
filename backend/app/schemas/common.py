from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    request_id: str
    correlation_id: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict[str, str]
    request_id: str
    correlation_id: str
