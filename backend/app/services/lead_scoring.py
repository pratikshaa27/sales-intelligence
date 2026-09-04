"""Transparent, rule-based lead scoring (spec §5): every point awarded is tied to a concrete,
inspectable condition and comes with a plain-English reason. The AI provider is never asked to
produce a bare number — spec §5 explicitly forbids "an unexplained score" — the only place AI
involvement enters the picture at all is one step upstream, in the research pipeline that
produces the evidence/company-profile fields this engine reads.

Score breakdown (spec §5): fit 30 + need 25 + authority 15 + timing 15 + confidence 15 = 100.
"""

import re
from dataclasses import dataclass, field

from app.models.company import Company
from app.models.contact import Contact, VerificationStatus
from app.models.product import Product
from app.models.research import EvidenceCategory, ResearchEvidence

SENIOR_KEYWORDS = [
    "chief",
    "ceo",
    "cto",
    "cio",
    "ciso",
    "cfo",
    "coo",
    "vp",
    "vice president",
    "head of",
    "director",
    "founder",
    "president",
]
_SIGNAL_CATEGORIES = {
    EvidenceCategory.HIRING_SIGNAL,
    EvidenceCategory.EXPANSION_SIGNAL,
    EvidenceCategory.DIGITAL_TRANSFORMATION_SIGNAL,
    EvidenceCategory.SECURITY_SIGNAL,
}
_TIMING_CATEGORIES = {EvidenceCategory.HIRING_SIGNAL, EvidenceCategory.EXPANSION_SIGNAL}
_STOPWORDS = {
    "with",
    "that",
    "this",
    "from",
    "have",
    "your",
    "their",
    "about",
    "into",
    "using",
    "such",
    "more",
    "than",
    "will",
    "which",
    "these",
    "those",
    "also",
    "some",
}


@dataclass
class ScoreBreakdown:
    total_score: int
    fit_score: int
    need_score: int
    authority_score: int
    timing_score: int
    confidence_score: int
    reasons: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]{4,}", text.lower()) if w not in _STOPWORDS}


def _keyword_overlap(a: list[str], b: list[str]) -> list[str]:
    words_a: set[str] = set()
    for t in a:
        words_a |= _keywords(t)
    words_b: set[str] = set()
    for t in b:
        words_b |= _keywords(t)
    return sorted(words_a & words_b)


def _score_fit(company: Company, product: Product, reasons: list[str], missing: list[str]) -> int:
    fit = 0
    if not product.target_industries:
        missing.append("Product has no target industries defined to compare against")
    elif company.industry and any(
        company.industry.lower() == t.lower() for t in product.target_industries
    ):
        fit += 12
        reasons.append(f"Company industry '{company.industry}' matches a target industry")
    else:
        missing.append("Company industry does not match (or is unknown against) target industries")

    if not product.target_company_size:
        missing.append("Product has no target company size defined to compare against")
    elif company.company_size and company.company_size in product.target_company_size:
        fit += 8
        reasons.append(f"Company size '{company.company_size}' matches a target company size")
    else:
        missing.append("Company size does not match (or is unknown against) target sizes")

    if company.locations and product.target_geographic_regions:
        if set(company.locations) & set(product.target_geographic_regions):
            fit += 5
            reasons.append("Company location matches a target geographic region")
    else:
        missing.append("No geographic region overlap could be evaluated")

    tech_overlap = set(company.technology_stack) & (
        set(product.supported_integrations) | set(product.required_technical_capabilities)
    )
    if tech_overlap:
        fit += 5
        overlap_str = ", ".join(sorted(tech_overlap))
        reasons.append(
            f"Company's technology stack overlaps with product compatibility: {overlap_str}"
        )

    return fit


def _score_need(
    company: Company,
    product: Product,
    evidence: list[ResearchEvidence],
    reasons: list[str],
    missing: list[str],
) -> int:
    need = 0
    overlap = _keyword_overlap(company.business_challenges, product.business_problems)
    if overlap:
        need += 15
        overlap_str = ", ".join(overlap)
        reasons.append(
            f"Company's stated challenges relate to problems this product solves: {overlap_str}"
        )
    else:
        missing.append(
            "No evidence yet connecting company's challenges to this product's problems solved"
        )

    signal_categories = {e.category for e in evidence if e.category in _SIGNAL_CATEGORIES}
    if signal_categories:
        need += 10
        reasons.append(
            "Public signals recorded: "
            + ", ".join(sorted(c.value.replace("_", " ") for c in signal_categories))
        )
    else:
        missing.append("No hiring/expansion/digital-transformation/security signals recorded yet")

    return need


def _score_authority(contact: Contact | None, reasons: list[str], missing: list[str]) -> int:
    if contact is None:
        missing.append("No decision-maker contact linked to this lead")
        return 0

    title_blob = f"{contact.seniority} {contact.job_title}".lower()
    is_senior = any(keyword in title_blob for keyword in SENIOR_KEYWORDS)
    is_verified = contact.verification_status == VerificationStatus.VERIFIED

    title = contact.job_title or contact.seniority
    if is_senior and is_verified:
        reasons.append(f"Linked contact '{title}' is senior and verified")
        return 15
    if is_senior:
        reasons.append(f"Linked contact '{title}' appears senior but is unverified")
        missing.append("Contact's seniority/role has not been verified")
        return 10
    reasons.append("A contact is linked, but their seniority doesn't clearly indicate authority")
    missing.append("No confirmed senior decision-maker identified for this company yet")
    return 5


def _score_timing(
    company: Company, evidence: list[ResearchEvidence], reasons: list[str], missing: list[str]
) -> int:
    timing_evidence = [e for e in evidence if e.category in _TIMING_CATEGORIES]
    if timing_evidence:
        reasons.append(
            f"{len(timing_evidence)} hiring/expansion signal(s) suggest active buying timing"
        )
        return 15
    if company.research_status == "researched":
        missing.append("No clear timing or buying signal identified in the current research")
        return 5
    missing.append("Company has not been researched yet — timing signals unknown")
    return 0


def _score_confidence(company: Company, reasons: list[str]) -> int:
    confidence = round(company.confidence_score / 100 * 15)
    reasons.append(f"Company research data confidence is {company.confidence_score}/100")
    return confidence


def calculate_lead_score(
    *,
    company: Company,
    product: Product,
    contact: Contact | None,
    evidence: list[ResearchEvidence],
) -> ScoreBreakdown:
    reasons: list[str] = []
    missing: list[str] = []

    fit = _score_fit(company, product, reasons, missing)
    need = _score_need(company, product, evidence, reasons, missing)
    authority = _score_authority(contact, reasons, missing)
    timing = _score_timing(company, evidence, reasons, missing)
    confidence = _score_confidence(company, reasons)

    total = min(fit + need + authority + timing + confidence, 100)

    return ScoreBreakdown(
        total_score=total,
        fit_score=fit,
        need_score=need,
        authority_score=authority,
        timing_score=timing,
        confidence_score=confidence,
        reasons=reasons,
        missing_information=missing,
    )


def score_to_priority(total_score: int) -> str:
    """Spec §5 score bands mapped onto the lead priority enum. >=80 -> high-priority lead
    (spec's own label); 60-79 and 40-59 both map to medium since spec doesn't distinguish a
    separate priority tier for "good potential" vs "needs more research"; <40 -> low. `critical`
    is reserved for manual escalation — nothing in the scoring rules implies it automatically.
    """
    if total_score >= 80:
        return "high"
    if total_score >= 40:
        return "medium"
    return "low"
