from app.models.company import Company, ResearchStatus
from app.models.contact import Contact, VerificationStatus
from app.models.product import Product
from app.models.research import EvidenceCategory, ResearchEvidence
from app.services.lead_scoring import calculate_lead_score, score_to_priority


def _company(**overrides) -> Company:
    defaults = dict(
        name="Acme Robotics",
        domain="acme.com",
        industry="Robotics",
        locations=["San Francisco, CA"],
        company_size="51-200",
        technology_stack=["AWS", "Kubernetes"],
        business_challenges=["Scaling manufacturing operations"],
        confidence_score=70,
        research_status=ResearchStatus.RESEARCHED,
    )
    defaults.update(overrides)
    return Company(**defaults)


def _product(**overrides) -> Product:
    defaults = dict(
        name="Acme Sales Copilot",
        code="SC-100",
        target_industries=["Robotics"],
        target_company_size=["51-200"],
        target_geographic_regions=["San Francisco, CA"],
        business_problems=["Manufacturing operations scaling is slow"],
        supported_integrations=["AWS"],
        required_technical_capabilities=[],
    )
    defaults.update(overrides)
    return Product(**defaults)


def _contact(**overrides) -> Contact:
    defaults = dict(
        full_name="Jamie Rivera",
        job_title="VP of Engineering",
        seniority="VP",
        verification_status=VerificationStatus.VERIFIED,
    )
    defaults.update(overrides)
    return Contact(**defaults)


def _evidence(category: EvidenceCategory) -> ResearchEvidence:
    return ResearchEvidence(
        category=category,
        fact_text="Company posted 20 new engineering job listings",
        source_url="https://acme.com/careers",
    )


def test_full_match_scores_high_with_reasons():
    breakdown = calculate_lead_score(
        company=_company(),
        product=_product(),
        contact=_contact(),
        evidence=[_evidence(EvidenceCategory.HIRING_SIGNAL)],
    )
    assert breakdown.total_score == 30 + 25 + 15 + 15 + round(70 / 100 * 15)
    assert breakdown.fit_score == 30
    assert breakdown.need_score == 25
    assert breakdown.authority_score == 15
    assert breakdown.timing_score == 15
    assert breakdown.missing_information == []
    assert breakdown.reasons
    assert score_to_priority(breakdown.total_score) == "high"


def test_no_match_scores_low_and_lists_missing_information():
    company = _company(
        industry="Retail",
        locations=["Nowhere"],
        company_size="1-10",
        technology_stack=[],
        business_challenges=[],
        confidence_score=0,
        research_status=ResearchStatus.NOT_RESEARCHED,
    )
    breakdown = calculate_lead_score(company=company, product=_product(), contact=None, evidence=[])
    assert breakdown.total_score == 0
    assert breakdown.fit_score == 0
    assert breakdown.need_score == 0
    assert breakdown.authority_score == 0
    assert breakdown.timing_score == 0
    assert breakdown.confidence_score == 0
    assert "No decision-maker contact linked to this lead" in breakdown.missing_information
    assert score_to_priority(breakdown.total_score) == "low"


def test_unverified_senior_contact_scores_partial_authority():
    breakdown = calculate_lead_score(
        company=_company(),
        product=_product(),
        contact=_contact(verification_status=VerificationStatus.UNVERIFIED),
        evidence=[],
    )
    assert breakdown.authority_score == 10
    assert any("unverified" in reason for reason in breakdown.reasons)


def test_junior_contact_scores_minimal_authority():
    breakdown = calculate_lead_score(
        company=_company(),
        product=_product(),
        contact=_contact(
            job_title="Software Engineer",
            seniority="",
            verification_status=VerificationStatus.VERIFIED,
        ),
        evidence=[],
    )
    assert breakdown.authority_score == 5


def test_score_never_exceeds_100():
    breakdown = calculate_lead_score(
        company=_company(confidence_score=100),
        product=_product(),
        contact=_contact(),
        evidence=[
            _evidence(EvidenceCategory.HIRING_SIGNAL),
            _evidence(EvidenceCategory.EXPANSION_SIGNAL),
        ],
    )
    assert breakdown.total_score <= 100


def test_score_to_priority_bands():
    assert score_to_priority(85) == "high"
    assert score_to_priority(80) == "high"
    assert score_to_priority(79) == "medium"
    assert score_to_priority(40) == "medium"
    assert score_to_priority(39) == "low"
    assert score_to_priority(0) == "low"
