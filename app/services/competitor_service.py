"""
Competitor service module.

In the baseline implementation, initial competitor identification is generated
by Google Gemini within the structured analysis prompt, labeled with:
`competitor_source: "AI-identified based on industry knowledge"`.

This service provides the architectural extension point for enriching competitor
intelligence with third-party competitive intelligence and market telemetry APIs
(e.g., SimilarWeb, SEMrush, Ahrefs, Crunchbase).
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CompetitorService:
    """Service for enriching competitor data with verified external data sources."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def enrich_competitors(
        self,
        brand_name: str,
        category: str,
        existing_competitors: Optional[list[Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Enrich competitor intelligence using external APIs.

        When no external intelligence provider is configured, this logs the
        telemetry and returns an empty list, allowing the LLM-derived competitor
        analysis to stand as AI-identified suggestions.

        When integrated (e.g., with SimilarWeb or SEMrush API), this method can:
        - Fetch organic keyword overlap and estimated traffic share
        - Verify company URLs and headquarter locations
        - Augment competitor strengths/weaknesses with measured metrics
        """
        if not self.api_key:
            logger.info(
                "CompetitorService: External intelligence provider not configured. "
                "Retaining LLM-derived competitor analysis for brand '%s' (%s).",
                brand_name,
                category,
            )
            return []

        # Example integration hook for future expansion:
        # return await self._fetch_similarweb_competitors(brand_name)
        return []
