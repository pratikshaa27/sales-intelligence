"""CSV column-mapping and row parsing for bulk import (spec §17). Pure and DB-independent —
duplicate-detection and entity creation happen one layer up in `import_service.py`/
`import_tasks.py`, which have repository access.

Column mapping is name-based rather than a free-form drag-and-drop remapping UI: a row's headers
are matched case-insensitively against each entity's known column names. This satisfies the spec's
"validate column mapping" requirement (missing required columns / unrecognized columns are both
surfaced) without building a much larger interactive remapping feature.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class FieldType(StrEnum):
    STR = "str"
    LIST = "list"
    INT = "int"
    FLOAT = "float"


@dataclass(frozen=True)
class ImportField:
    csv_column: str
    model_field: str
    field_type: FieldType = FieldType.STR
    required: bool = False


COMPANY_FIELDS: list[ImportField] = [
    ImportField("name", "name", required=True),
    ImportField("website", "website", required=True),
    ImportField("industry", "industry"),
    ImportField("locations", "locations", FieldType.LIST),
    ImportField("company_size", "company_size"),
    ImportField("revenue_range", "revenue_range"),
    ImportField("business_description", "business_description"),
    ImportField("technology_stack", "technology_stack", FieldType.LIST),
    ImportField("business_challenges", "business_challenges", FieldType.LIST),
    ImportField("public_signals", "public_signals", FieldType.LIST),
    ImportField("confidence_score", "confidence_score", FieldType.INT),
]

CONTACT_FIELDS: list[ImportField] = [
    ImportField("company_website", "company_website", required=True),
    ImportField("full_name", "full_name", required=True),
    ImportField("job_title", "job_title"),
    ImportField("department", "department"),
    ImportField("seniority", "seniority"),
    ImportField("role_relevance", "role_relevance"),
    ImportField("profile_url", "profile_url"),
    ImportField("business_email", "business_email"),
    ImportField("business_phone", "business_phone"),
    ImportField("confidence_score", "confidence_score", FieldType.INT),
]

PRODUCT_FIELDS: list[ImportField] = [
    ImportField("name", "name", required=True),
    ImportField("code", "code", required=True),
    ImportField("short_description", "short_description"),
    ImportField("detailed_description", "detailed_description"),
    ImportField("target_industries", "target_industries", FieldType.LIST),
    ImportField("target_company_size", "target_company_size", FieldType.LIST),
    ImportField("target_geographic_regions", "target_geographic_regions", FieldType.LIST),
    ImportField("business_problems", "business_problems", FieldType.LIST),
    ImportField("key_features", "key_features", FieldType.LIST),
    ImportField("benefits", "benefits", FieldType.LIST),
    ImportField("pricing_model", "pricing_model"),
    ImportField("minimum_contract_value", "minimum_contract_value", FieldType.FLOAT),
    ImportField(
        "required_technical_capabilities", "required_technical_capabilities", FieldType.LIST
    ),
    ImportField("supported_integrations", "supported_integrations", FieldType.LIST),
    ImportField("ideal_customer_profile", "ideal_customer_profile"),
    ImportField("common_use_cases", "common_use_cases", FieldType.LIST),
    ImportField("competitor_alternatives", "competitor_alternatives", FieldType.LIST),
]

LEAD_FIELDS: list[ImportField] = [
    ImportField("company_website", "company_website", required=True),
    ImportField("product_code", "product_code", required=True),
    ImportField("contact_email", "contact_email"),
    ImportField("name", "name", required=True),
    ImportField("source", "source"),
    ImportField("tags", "tags", FieldType.LIST),
]

FIELD_SPECS: dict[str, list[ImportField]] = {
    "company": COMPANY_FIELDS,
    "contact": CONTACT_FIELDS,
    "product": PRODUCT_FIELDS,
    "lead": LEAD_FIELDS,
}


class RowParseError(ValueError):
    pass


def parse_value(raw: str, field_type: FieldType) -> object:
    raw = raw.strip()
    if field_type == FieldType.LIST:
        return [v.strip() for v in raw.split(";") if v.strip()]
    if not raw:
        return None if field_type in (FieldType.INT, FieldType.FLOAT) else ""
    if field_type == FieldType.INT:
        try:
            return int(raw)
        except ValueError as exc:
            raise RowParseError(f"'{raw}' is not a whole number") from exc
    if field_type == FieldType.FLOAT:
        try:
            return float(raw)
        except ValueError as exc:
            raise RowParseError(f"'{raw}' is not a number") from exc
    return raw


@dataclass
class HeaderValidation:
    missing_required: list[str] = field(default_factory=list)
    unknown_columns: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.missing_required


def validate_headers(entity_type: str, header_row: list[str]) -> HeaderValidation:
    spec = FIELD_SPECS[entity_type]
    normalized = {h.strip().lower() for h in header_row}
    missing = [f.csv_column for f in spec if f.required and f.csv_column not in normalized]
    known = {f.csv_column for f in spec}
    unknown = [h for h in header_row if h.strip().lower() not in known]
    return HeaderValidation(missing_required=missing, unknown_columns=unknown)


@dataclass
class ParsedRow:
    row_number: int
    values: dict[str, object]
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def parse_row(entity_type: str, row_number: int, row: dict[str, str]) -> ParsedRow:
    spec = FIELD_SPECS[entity_type]
    normalized_row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
    values: dict[str, object] = {}
    errors: list[str] = []

    for f in spec:
        raw = normalized_row.get(f.csv_column, "")
        if f.required and not raw.strip():
            errors.append(f"Missing required value for '{f.csv_column}'")
            continue
        try:
            values[f.model_field] = parse_value(raw, f.field_type)
        except RowParseError as exc:
            errors.append(f"Column '{f.csv_column}': {exc}")

    return ParsedRow(row_number=row_number, values=values, errors=errors)
