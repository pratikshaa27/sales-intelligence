"""AI provider abstraction (spec §2/§14): callers depend only on this interface, never on a
specific vendor SDK, so swapping providers never touches business logic. Covers embeddings
(product matching), structured completions (research extraction), and conversation-starter
generation for sales briefs.
"""

import hashlib
import json
import logging
import random
import re
from abc import ABC, abstractmethod

import httpx

from app.ai.prompts import (
    COMPANY_PROFILE_SYSTEM_PROMPT,
    SALES_BRIEF_SYSTEM_PROMPT,
    build_company_profile_user_prompt,
    build_sales_brief_user_prompt,
)
from app.ai.schemas import ConversationStarters, ExtractedCompanyProfile
from app.core.config import get_settings
from app.models.product import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


class EmbeddingProviderError(Exception):
    """Raised when an embedding could not be generated; never silently returns a fake vector."""


class CompletionProviderError(Exception):
    """Raised when a structured completion could not be generated or failed validation; never
    silently returns a fake/unvalidated result."""


class EmbeddingProvider(ABC):
    name: str
    dimensions: int = EMBEDDING_DIMENSIONS

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding for local/dev/test use — same text always produces the
    same vector, but it carries no real semantic meaning. Never used unless AI_PROVIDER=mock."""

    name = "mock"

    async def embed(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        vector = [rng.uniform(-1.0, 1.0) for _ in range(self.dimensions)]
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Works against OpenAI itself or any OpenAI-compatible embeddings endpoint (local Ollama,
    vLLM, LM Studio, etc.) — AI_BASE_URL should include the version prefix the provider expects
    (e.g. https://api.openai.com/v1)."""

    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url:
            raise EmbeddingProviderError(
                "AI_BASE_URL must be set for AI_PROVIDER=openai_compatible"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def embed(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                payload = response.json()
            return payload["data"][0]["embedding"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.error("embedding_provider_request_failed", extra={"error": str(exc)})
            raise EmbeddingProviderError(f"Embedding request failed: {exc}") from exc


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.embedding_model,
        )
    return MockEmbeddingProvider()


class CompletionProvider(ABC):
    name: str

    @abstractmethod
    async def extract_company_profile(
        self, *, company_name: str, webpage_text: str
    ) -> ExtractedCompanyProfile: ...


_TECH_KEYWORDS = [
    "AWS",
    "Amazon Web Services",
    "Microsoft Azure",
    "Azure",
    "Google Cloud",
    "GCP",
    "Kubernetes",
    "Docker",
    "React",
    "Angular",
    "Vue",
    "Python",
    "Java",
    "Salesforce",
    "HubSpot",
    "Snowflake",
    "PostgreSQL",
    "MongoDB",
    "Kafka",
    "microservices",
    "machine learning",
    "artificial intelligence",
]
_HIRING_PHRASES = [
    "we're hiring",
    "we are hiring",
    "join our team",
    "open positions",
    "join us",
    "growing our team",
    "careers page",
]
_EXPANSION_PHRASES = [
    "new office",
    "expanding into",
    "now available in",
    "opened a new",
    "expanding our team",
    "series a",
    "series b",
    "raised funding",
    "secured funding",
]


class MockCompletionProvider(CompletionProvider):
    """Deterministic keyword-spotting over the fetched text — not real language understanding.

    Unlike embeddings, there's no principled way to mock "infer business challenges from prose",
    so this only ever fills in categories a simple keyword match can defend (tech stack, hiring,
    expansion); business_challenges is always left empty here rather than guessed. Never used
    unless AI_PROVIDER=mock.
    """

    name = "mock"

    async def extract_company_profile(
        self, *, company_name: str, webpage_text: str
    ) -> ExtractedCompanyProfile:
        text_lower = webpage_text.lower()

        technology_stack = sorted({kw for kw in _TECH_KEYWORDS if kw.lower() in text_lower})
        hiring_signals = [p for p in _HIRING_PHRASES if p in text_lower]
        expansion_signals = [p for p in _EXPANSION_PHRASES if p in text_lower]

        overview = webpage_text[:280].strip()
        signal_count = sum(bool(x) for x in (technology_stack, hiring_signals, expansion_signals))
        confidence = 0
        if webpage_text.strip():
            confidence = min(30 + 15 * signal_count + min(len(webpage_text) // 500, 20), 90)

        return ExtractedCompanyProfile(
            overview=overview,
            technology_stack=technology_stack,
            hiring_signals=hiring_signals,
            expansion_signals=expansion_signals,
            business_challenges=[],
            confidence=confidence,
        )


class OpenAICompatibleCompletionProvider(CompletionProvider):
    """Works against OpenAI itself or any OpenAI-compatible chat-completions endpoint. The
    response is always validated against ExtractedCompanyProfile before being trusted — an
    unparseable or schema-violating reply raises CompletionProviderError rather than being used."""

    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url:
            raise CompletionProviderError(
                "AI_BASE_URL must be set for AI_PROVIDER=openai_compatible"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def extract_company_profile(
        self, *, company_name: str, webpage_text: str
    ) -> ExtractedCompanyProfile:
        parsed = await _chat_completion_json(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            system_prompt=COMPANY_PROFILE_SYSTEM_PROMPT,
            user_prompt=build_company_profile_user_prompt(
                company_name=company_name, webpage_text=webpage_text
            ),
        )
        try:
            return ExtractedCompanyProfile.model_validate(parsed)
        except ValueError as exc:
            logger.error("completion_provider_invalid_response", extra={"error": str(exc)})
            raise CompletionProviderError(
                f"Model response did not match the expected schema: {exc}"
            ) from exc


def get_completion_provider() -> CompletionProvider:
    settings = get_settings()
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleCompletionProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
        )
    return MockCompletionProvider()


async def _chat_completion_json(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800,
) -> dict:
    """Shared OpenAI-compatible chat-completions call used by every structured-output provider
    below: sends the request, strips a markdown fence some models add despite instructions not
    to, and parses the result as JSON. Callers still validate the parsed dict against their own
    Pydantic schema — this only guarantees "valid JSON", not "matches what we asked for"."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
        "temperature": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            body = response.json()
        raw_content = body["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.error("completion_provider_request_failed", extra={"error": str(exc)})
        raise CompletionProviderError(f"Completion request failed: {exc}") from exc

    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_content.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("completion_provider_invalid_response", extra={"error": str(exc)})
        raise CompletionProviderError(f"Model response was not valid JSON: {exc}") from exc


class BriefProvider(ABC):
    name: str

    @abstractmethod
    async def generate_conversation_starters(
        self,
        *,
        company_name: str,
        product_name: str,
        business_problem: str,
        evidence_bullets: list[str],
        decision_maker: str,
    ) -> ConversationStarters: ...


class MockBriefProvider(BriefProvider):
    """Deterministic templated text — not real language generation. Clearly generic rather than
    inventing specifics the underlying data doesn't support. Never used unless AI_PROVIDER=mock."""

    name = "mock"

    async def generate_conversation_starters(
        self,
        *,
        company_name: str,
        product_name: str,
        business_problem: str,
        evidence_bullets: list[str],
        decision_maker: str,
    ) -> ConversationStarters:
        if business_problem:
            opener = (
                f"Hi — I noticed {company_name} has been dealing with {business_problem}. "
                f"We've helped similar teams with {product_name}, and I'd love to hear how "
                "you're approaching it today."
            )
        else:
            opener = (
                f"Hi — I've been following {company_name}'s progress and thought {product_name} "
                "might be relevant to what your team is working on. Would you be open to a "
                "short conversation?"
            )
        questions = [
            "What's currently the biggest bottleneck in this area for your team?",
            "How are you handling this today, and what's working well or not?",
            "Who else would be involved in evaluating a change here?",
        ]
        if evidence_bullets:
            questions.insert(
                0, f"I saw that {evidence_bullets[0].lower()} — could you tell me more about that?"
            )
        return ConversationStarters(suggested_opener=opener, discovery_questions=questions[:6])


class OpenAICompatibleBriefProvider(BriefProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str):
        if not base_url:
            raise CompletionProviderError(
                "AI_BASE_URL must be set for AI_PROVIDER=openai_compatible"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def generate_conversation_starters(
        self,
        *,
        company_name: str,
        product_name: str,
        business_problem: str,
        evidence_bullets: list[str],
        decision_maker: str,
    ) -> ConversationStarters:
        parsed = await _chat_completion_json(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            system_prompt=SALES_BRIEF_SYSTEM_PROMPT,
            user_prompt=build_sales_brief_user_prompt(
                company_name=company_name,
                product_name=product_name,
                business_problem=business_problem,
                evidence_bullets=evidence_bullets,
                decision_maker=decision_maker,
            ),
            max_tokens=500,
        )
        try:
            return ConversationStarters.model_validate(parsed)
        except ValueError as exc:
            logger.error("brief_provider_invalid_response", extra={"error": str(exc)})
            raise CompletionProviderError(
                f"Model response did not match the expected schema: {exc}"
            ) from exc


def get_brief_provider() -> BriefProvider:
    settings = get_settings()
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleBriefProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
        )
    return MockBriefProvider()
