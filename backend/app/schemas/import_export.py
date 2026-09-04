import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.import_job import ImportEntityType, ImportJobStatus
from app.models.lead import LeadPriority, LeadStatus


class RowErrorOut(BaseModel):
    row: int
    errors: list[str]


class ImportPreviewResponse(BaseModel):
    entity_type: ImportEntityType
    total_rows: int
    missing_required_columns: list[str]
    unknown_columns: list[str]
    valid_row_count: int
    invalid_row_count: int
    sample_errors: list[RowErrorOut]
    can_proceed: bool


class ImportJobOut(BaseModel):
    id: uuid.UUID
    entity_type: ImportEntityType
    status: ImportJobStatus
    file_name: str
    progress_percentage: int
    current_step: str
    logs: list[str]
    total_rows: int
    processed_rows: int
    created_count: int
    skipped_count: int
    error_count: int
    row_errors: list[dict]
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExportLeadsRequest(BaseModel):
    format: str = "csv"  # "csv" | "csv_excel" | "json"
    status: LeadStatus | None = None
    priority: LeadPriority | None = None
    product_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    min_score: int | None = None
