"""Export request/response schemas."""

from pydantic import Field

from app.schemas.common import CamelModel


class ExportRequest(CamelModel):
    format: str = Field("csv", description="csv | json")
    period_start: str | None = None
    period_end: str | None = None
    partner_id: str | None = None


class ExportResponse(CamelModel):
    id: str
    filename: str
    format: str
    period_start: str
    period_end: str
    record_count: int
    created_at: str


class ExportListResponse(CamelModel):
    exports: list[ExportResponse]
