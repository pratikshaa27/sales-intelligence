import csv
import io
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.repositories.lead_repository import LeadRepository
from app.schemas.import_export import ExportLeadsRequest

MAX_EXPORT_ROWS = 5000
_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\t", "\r")
EXPORT_COLUMNS = [
    "id",
    "name",
    "status",
    "priority",
    "total_score",
    "fit_score",
    "need_score",
    "authority_score",
    "timing_score",
    "data_confidence_score",
    "company_name",
    "product_name",
    "assigned_to_name",
    "contact_name",
    "contact_job_title",
    "contact_email",
    "contact_phone",
    "source",
    "next_action",
    "tags",
    "created_at",
    "updated_at",
]


def _escape_csv_formula_value(value: object) -> object:
    """Excel/Sheets treat a leading =, +, -, or @ as the start of a formula — a lead/company/
    product name containing one would otherwise execute as a formula for whoever opens the
    export (classic CSV-injection). Prefixing a single quote forces it to render as literal
    text; Excel strips the quote on display."""
    if isinstance(value, str) and value.startswith(_FORMULA_TRIGGER_CHARS):
        return "'" + value
    return value


def _escape_csv_row(record: dict) -> dict:
    return {k: _escape_csv_formula_value(v) for k, v in record.items()}


class ExportService:
    """Lead export (spec §17/§13 step 13). Only Leads are exportable: spec's API list names
    exactly `POST /leads/export` and only `leads.export` exists as a permission — companies/
    contacts/products export was never specified as a separate surface."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.leads = LeadRepository(db)

    async def export_leads(
        self, *, organization_id: uuid.UUID, body: ExportLeadsRequest
    ) -> tuple[bytes, str, str]:
        if body.format not in ("csv", "csv_excel", "json"):
            raise AppError("VALIDATION_ERROR", f"Unsupported export format '{body.format}'", 422)

        rows = await self.leads.list_for_export(
            organization_id=organization_id,
            status=body.status,
            priority=body.priority,
            product_id=body.product_id,
            company_id=body.company_id,
            assigned_to=body.assigned_to,
            min_score=body.min_score,
            limit=MAX_EXPORT_ROWS,
        )

        records = [
            {
                "id": str(lead.id),
                "name": lead.name,
                "status": lead.status.value,
                "priority": lead.priority.value,
                "total_score": lead.total_score,
                "fit_score": lead.fit_score,
                "need_score": lead.need_score,
                "authority_score": lead.authority_score,
                "timing_score": lead.timing_score,
                "data_confidence_score": lead.data_confidence_score,
                "company_name": company_name,
                "product_name": product_name,
                "assigned_to_name": assigned_full_name or "",
                "contact_name": contact.full_name if contact else "",
                "contact_job_title": contact.job_title if contact else "",
                "contact_email": contact.business_email if contact else "",
                "contact_phone": contact.business_phone if contact else "",
                "source": lead.source,
                "next_action": lead.next_action,
                "tags": ";".join(lead.tags),
                "created_at": lead.created_at.isoformat(),
                "updated_at": lead.updated_at.isoformat(),
            }
            for lead, company_name, product_name, assigned_full_name, contact in rows
        ]

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        if body.format == "json":
            content = json.dumps(records, indent=2).encode("utf-8")
            return content, "application/json", f"leads_export_{timestamp}.json"

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(_escape_csv_row(r) for r in records)
        csv_text = buffer.getvalue()

        if body.format == "csv_excel":
            # A leading UTF-8 BOM is what makes Excel open a UTF-8 CSV without mangling
            # non-ASCII characters — the only real difference from plain "csv" (spec §17).
            bom = chr(0xFEFF)
            return (
                (bom + csv_text).encode("utf-8"),
                "text/csv",
                f"leads_export_{timestamp}_excel.csv",
            )

        return csv_text.encode("utf-8"), "text/csv", f"leads_export_{timestamp}.csv"
