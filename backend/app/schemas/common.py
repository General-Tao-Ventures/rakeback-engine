"""Common/shared schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model that serializes snake_case fields as camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class PaginatedResponse(CamelModel, Generic[T]):
    total: int
    page: int
    items: list[T]


class ErrorResponse(BaseModel):
    detail: str
    type: str | None = None


class HealthResponse(BaseModel):
    status: str
