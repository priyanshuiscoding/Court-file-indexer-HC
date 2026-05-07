from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HighCourtImportRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)


class HighCourtImportItemResult(BaseModel):
    external_row_id: int | str | None = None
    batch_no: str | None = None
    fil_no: str | None = None
    pdf_path: str | None = None
    status: str
    document_id: int | None = None
    error: str | None = None


class HighCourtImportResponse(BaseModel):
    ok: bool
    requested_limit: int | None = None
    scan_limit: int | None = None
    scanned: int | None = None
    fetched: int
    imported: int
    queued: int
    skipped: int
    skipped_existing: int = 0
    pdf_not_found: int = 0
    failed: int
    results: list[HighCourtImportItemResult]


class HighCourtImportJobOut(BaseModel):
    id: int
    source_system: str
    external_row_id: str | None = None
    batch_no: str
    fil_no: str | None = None
    source_pdf_path: str | None = None
    document_id: int | None = None
    status: str
    error_message: str | None = None
    import_attempts: int
    last_attempt_at: datetime | None = None
    imported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HighCourtImportJobListResponse(BaseModel):
    ok: bool
    count: int
    jobs: list[HighCourtImportJobOut]


class HighCourtRetryRequest(BaseModel):
    batch_no: str


class HighCourtImportStatusSyncResponse(BaseModel):
    ok: bool
    checked: int
    updated: int


class HighCourtMarkCompleteRequest(BaseModel):
    batch_no: str


class HighCourtBulkMarkCompleteRequest(BaseModel):
    limit: int | None = Field(default=100, ge=1, le=500)
