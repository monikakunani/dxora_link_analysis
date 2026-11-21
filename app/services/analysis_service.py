import logging
from app.services.website_extractor import WebsiteExtractor
from app.services.llm_service import LLMService
from app.services.competitor_service import CompetitorService
from app.services.cache_service import analysis_cache
from app.schemas import (
    LinkAnalysisResponse,
    BrandInfo,
    BrandProfile,
    Analysis,
    CompetitorAnalysis,
    Competitor,
    SearchQuery,
    SEOImprovements,
    SupportingContent,
    Service,
    TargetAudience,
    AudienceSegment,
)

logger = logging.getLogger(__name__)

# Required counts as specified in the assignment
REQUIRED_SEARCH_QUERIES = 5
REQUIRED_TOP_SERVICES = 5
REQUIRED_COMPETITORS = 3        # prompt says "EXACTLY 3"; enforce at both ends
MIN_SUPPORTING_CONTENT = 3      # prompt says "at least 3"


class AnalysisOutputError(ValueError):
    """The model did not return the minimum required response sections."""


class AnalysisService:
    """Orchestrates website extraction, LLM analysis, caching, and enrichment."""

    def __init__(self):
        self.extractor = WebsiteExtractor()
        self.llm = LLMService()
        self.competitor_service = CompetitorService()

    async def analyze(self, url: str) -> LinkAnalysisResponse:
        """Run the full analysis pipeline for a given URL."""
        # Step 1: Return cached result if available
        cached = await analysis_cache.get(url)
        if cached is not None:
            logger.info("Returning cached analysis for %s", url)
            return cached

        # Step 2: Extract website content
        website_content = await self.extractor.extract(url)

        # Step 3: Send to LLM for analysis
        raw = await self.llm.analyze(website_content)

        # Step 4: Validate and structure the response
        result = self._build_response(url, raw)

        # Step 5: Competitor enrichment (no-op until an external API is wired
        # in; CompetitorService logs and retains LLM-derived suggestions by default).
        await self.competitor_service.enrich_competitors(
            result.brand.name,
            result.brand.category,
            result.analysis.competitor_analysis.competitors,
        )

        # Step 6: Cache the validated result
        await analysis_cache.set(url, result)

        return result

    def _build_response(self, url: str, raw: dict) -> LinkAnalysisResponse:
        """Build a fully validated Pydantic response from raw LLM output."""
        if not isinstance(raw, dict):
            raise AnalysisOutputError("The analysis provider returned an invalid response.")
        brand_raw = raw.get("brand", {})
        analysis_raw = raw.get("analysis", {})
        if not isinstance(brand_raw, dict) or not isinstance(analysis_raw, dict):
            raise AnalysisOutputError("The analysis provider omitted required response sections.")

        # Brand
        brand = BrandInfo(
            name=brand_raw.get("name", "Unknown"),
            category=brand_raw.get("category", "Unknown"),
            summary=brand_raw.get("summary", "No summary available."),
        )

        # Section 1: Competitor Analysis
        comp_raw = analysis_raw.get("competitor_analysis", {})
        competitors = [
            Competitor(**c) for c in comp_raw.get("competitors", [])
        ]

        # Enforce exactly REQUIRED_COMPETITORS — matches the LLM prompt constraint.
        if len(competitors) != REQUIRED_COMPETITORS:
            raise AnalysisOutputError(
                f"The analysis provider returned {len(competitors)} competitor(s); "
                f"exactly {REQUIRED_COMPETITORS} are required."
            )

        your_brand_raw = comp_raw.get("your_brand")
        competitor_analysis = CompetitorAnalysis(
            brand_overview=comp_raw.get("brand_overview", ""),
            business_category=comp_raw.get("business_category", ""),
            main_products_services=comp_raw.get("main_products_services", []),
            your_brand=BrandProfile(**your_brand_raw) if isinstance(your_brand_raw, dict) else None,
            competitors=competitors,
            brand_strengths=comp_raw.get("brand_strengths", []),
            opportunities=comp_raw.get("opportunities", []),
        )

        # Section 2: Target Search Queries — enforce exactly 5
        raw_queries = analysis_raw.get("target_search_queries", [])
        queries = [SearchQuery(**q) for q in raw_queries]
        if len(queries) != REQUIRED_SEARCH_QUERIES:
            raise AnalysisOutputError(
                f"The analysis provider returned {len(queries)} search queries; "
                f"exactly {REQUIRED_SEARCH_QUERIES} are required."
            )

        # Section 3: SEO Improvements
        seo_raw = analysis_raw.get("seo_improvements", {})
        supporting = [
            SupportingContent(**s)
            for s in seo_raw.get("supporting_content", [])
        ]
        # Enforce minimum supporting content suggestions
        if len(supporting) < MIN_SUPPORTING_CONTENT:
            raise AnalysisOutputError(
                f"The analysis provider returned {len(supporting)} supporting content "
                f"suggestion(s); at least {MIN_SUPPORTING_CONTENT} are required."
            )
        seo = SEOImprovements(
            primary_keyword=seo_raw.get("primary_keyword", ""),
            secondary_keywords=seo_raw.get("secondary_keywords", []),
            long_tail_keywords=seo_raw.get("long_tail_keywords", []),
            business_keywords=seo_raw.get("business_keywords", []),
            recommended_title=seo_raw.get("recommended_title", ""),
            title_primary_keyword=seo_raw.get("title_primary_keyword", ""),
            title_structure_notes=seo_raw.get("title_structure_notes", ""),
            meta_description=seo_raw.get("meta_description", ""),
            business_summary=seo_raw.get("business_summary", ""),
            meta_keywords=seo_raw.get("meta_keywords", []),
            supporting_content=supporting,
        )

        # Section 4: Top Services — enforce exactly 5
        raw_services = analysis_raw.get("top_services", [])
        services = [Service(**s) for s in raw_services]
        if len(services) != REQUIRED_TOP_SERVICES:
            raise AnalysisOutputError(
                f"The analysis provider returned {len(services)} service(s); "
                f"exactly {REQUIRED_TOP_SERVICES} are required."
            )

        # Section 5: Target Audience
        ta_raw = analysis_raw.get("target_audience", {})
        target_audience = TargetAudience(
            primary_audience=[
                AudienceSegment(**a) for a in ta_raw.get("primary_audience", [])
            ],
            secondary_audience=[
                AudienceSegment(**a) for a in ta_raw.get("secondary_audience", [])
            ],
            industries=ta_raw.get("industries", []),
            business_types=ta_raw.get("business_types", []),
            customer_profiles=ta_raw.get("customer_profiles", []),
            customer_needs=ta_raw.get("customer_needs", []),
            geographical_focus=ta_raw.get("geographical_focus"),
            customer_interests=ta_raw.get("customer_interests", []),
            recommended_segments=ta_raw.get("recommended_segments", []),
        )

        # Assemble
        analysis = Analysis(
            competitor_analysis=competitor_analysis,
            target_search_queries=queries,
            seo_improvements=seo,
            top_services=services,
            target_audience=target_audience,
        )

        return LinkAnalysisResponse(
            success=True,
            website=url,
            brand=brand,
            analysis=analysis,
        )
