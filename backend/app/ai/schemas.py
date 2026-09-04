"""Structured output schemas for AI extraction (spec §14: use structured output schemas,
validate all AI responses — nothing from a provider is trusted until it parses against one of
these).
"""

from pydantic import BaseModel, Field


class ExtractedCompanyProfile(BaseModel):
    """What the completion provider is allowed to report about a company's own website.

    Every field must be grounded in the webpage text actually provided — the extraction prompt
    (see app/ai/prompts.py) instructs the model to leave a category empty rather than guess, and
    this schema itself doesn't accept anything unstructured that could smuggle in an invented
    claim.
    """

    overview: str = Field(default="", max_length=1000)
    technology_stack: list[str] = Field(default_factory=list)
    hiring_signals: list[str] = Field(default_factory=list)
    expansion_signals: list[str] = Field(default_factory=list)
    business_challenges: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class DiscoveredCompanyCandidate(BaseModel):
    name: str
    website: str
    industry: str = ""
    company_size: str = ""
    rationale: str = ""


class ConversationStarters(BaseModel):
    """The only AI-generated parts of a sales brief (spec §7): every other field (company
    overview, evidence, score, missing information) is populated directly from the database, not
    by the model. The prompt (see app/ai/prompts.py) instructs the model to reference only the
    facts it's given and never invent a detail, but this schema also can't carry anything beyond
    plain opener/question text, so there's nowhere for a fabricated "fact" to be smuggled in.
    """

    suggested_opener: str = Field(default="", max_length=1000)
    discovery_questions: list[str] = Field(default_factory=list, max_length=6)
