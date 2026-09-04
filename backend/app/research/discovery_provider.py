"""Company discovery data-source abstraction (spec §4.4). No real data provider (a licensed B2B
data API, business directory, etc.) is configured for this deployment, so only a mock/local
implementation exists — per spec §30, this must never be presented as real production data. Every
candidate the mock returns is obviously synthetic (name, domain, and an explicit rationale label)
and the job result additionally flags `is_mock_data: true` so nothing downstream can mistake it
for a real lead.
"""

import re
from abc import ABC, abstractmethod

from app.ai.schemas import DiscoveredCompanyCandidate

MAX_MOCK_CANDIDATES = 5


class DiscoveryProvider(ABC):
    name: str
    is_mock: bool

    @abstractmethod
    async def discover_companies(
        self,
        *,
        industry: str,
        location: str,
        company_size: str,
        keywords: list[str],
        limit: int,
    ) -> list[DiscoveredCompanyCandidate]: ...


class MockDiscoveryProvider(DiscoveryProvider):
    name = "mock"
    is_mock = True

    async def discover_companies(
        self,
        *,
        industry: str,
        location: str,
        company_size: str,
        keywords: list[str],
        limit: int,
    ) -> list[DiscoveredCompanyCandidate]:
        seed_terms = [t for t in [industry, *keywords] if t] or ["General"]
        count = min(limit, MAX_MOCK_CANDIDATES)

        candidates = []
        for i in range(count):
            label = seed_terms[i % len(seed_terms)]
            slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "sample"
            candidates.append(
                DiscoveredCompanyCandidate(
                    name=f"Sample {label} Company {i + 1}",
                    website=f"https://sample-{slug}-{i + 1}.example.com",
                    industry=industry,
                    company_size=company_size,
                    rationale=(
                        "[MOCK DATA — not a real company] Illustrates matching on "
                        f"industry={industry or 'any'}, location={location or 'any'}, "
                        f"keywords={keywords or 'none'}. Configure a real data provider "
                        "before using discovery results for actual prospecting."
                    ),
                )
            )
        return candidates


def get_discovery_provider() -> DiscoveryProvider:
    return MockDiscoveryProvider()
