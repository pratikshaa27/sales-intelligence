from app.services.import_mapping import FieldType, parse_row, parse_value, validate_headers


def test_validate_headers_detects_missing_required_columns():
    validation = validate_headers("company", ["Name", "industry"])
    assert "website" in validation.missing_required
    assert not validation.is_valid


def test_validate_headers_is_case_insensitive_and_flags_unknown_columns():
    validation = validate_headers("company", ["NAME", "Website", "  Industry  ", "carrier_pigeon"])
    assert validation.missing_required == []
    assert validation.is_valid
    assert "carrier_pigeon" in validation.unknown_columns


def test_parse_value_list_splits_on_semicolon_and_trims():
    assert parse_value(" AWS ; Kubernetes ;; ", FieldType.LIST) == ["AWS", "Kubernetes"]
    assert parse_value("", FieldType.LIST) == []


def test_parse_value_int_and_float():
    assert parse_value("42", FieldType.INT) == 42
    assert parse_value("", FieldType.INT) is None
    assert parse_value("3.5", FieldType.FLOAT) == 3.5
    assert parse_value("", FieldType.FLOAT) is None


def test_parse_row_company_success():
    row = {
        "name": "Acme Robotics",
        "website": "https://acme.com",
        "industry": "Robotics",
        "locations": "SF; NYC",
        "confidence_score": "70",
    }
    parsed = parse_row("company", 2, row)
    assert parsed.is_valid, parsed.errors
    assert parsed.values["name"] == "Acme Robotics"
    assert parsed.values["locations"] == ["SF", "NYC"]
    assert parsed.values["confidence_score"] == 70


def test_parse_row_missing_required_field_reports_error():
    row = {"name": "", "website": "https://acme.com"}
    parsed = parse_row("company", 3, row)
    assert not parsed.is_valid
    assert any("name" in e for e in parsed.errors)


def test_parse_row_invalid_number_reports_error_not_crash():
    row = {"name": "Acme", "website": "https://acme.com", "confidence_score": "not-a-number"}
    parsed = parse_row("company", 4, row)
    assert not parsed.is_valid
    assert any("confidence_score" in e for e in parsed.errors)


def test_parse_row_lead_natural_keys():
    row = {
        "company_website": "https://acme.com",
        "product_code": "SC-100",
        "contact_email": "",
        "name": "Acme - Sales Copilot",
        "source": "csv_import",
        "tags": "hot;q3",
    }
    parsed = parse_row("lead", 2, row)
    assert parsed.is_valid, parsed.errors
    assert parsed.values["company_website"] == "https://acme.com"
    assert parsed.values["product_code"] == "SC-100"
    assert parsed.values["tags"] == ["hot", "q3"]
