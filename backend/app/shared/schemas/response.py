from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class StandardResponse(BaseModel, Generic[T]):
    status: str = "ok"
    data: T
    meta: dict | None = None  # type: ignore[type-arg]
    errors: list[ErrorDetail] = []


class PaginatedResponse(BaseModel, Generic[T]):
    status: str = "ok"
    data: list[T]
    meta: PaginationMeta
    errors: list[ErrorDetail] = []
