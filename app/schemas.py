from pydantic import BaseModel, HttpUrl, Field
from typing import Literal, Optional


# ── Request ──────────────────────────────────────────────────────────────────

class LinkAnalysisRequest(BaseModel):
    """Request body for the link-analysis endpoint."""
    url: HttpUrl = Field(..., description="The website URL to analyze", examples=["https://example.com"])


# ── Competitor Analysis ──────────────────────────────────────────────────────

class Competitor(BaseModel):
    """Details of an identified competitor."""
    name: str = Field("Unknown", description="Competitor brand name")
    main_service: str = Field("", description="Competitor's main service or product")
    target_market: str = Field("", description="Competitor's target market")
    key_strength: str = Field("", description="Competitor's key strength")
    weakness_or_gap: str = Field("", description="Competitor's weakness or gap")
    opportunity: str = Field("", description="Opportunity against this competitor")
    competitor_source: Literal["AI-identified based on industry knowledge", "website"] = Field(
        "AI-identified based on industry knowledge",
        description="Source of competitor identification: 'AI-identified based on industry knowledge' or 'website' if mentioned on the analyzed site",
    )


class BrandProfile(BaseModel):
    """The analyzed brand's own row in the 'Your Brand vs Competitor' comparison."""
    name: str = Field("", description="Your brand name")
    main_service: str = Field("", description="Your brand's main service or product")
    target_market: str = Field("", description="Your brand's target market")
    key_strength: str = Field("", description="Your brand's key strength")
    opportunity: str = Field("", description="Your brand's biggest positioning opportunity")


class CompetitorAnalysis(BaseModel):
    """Section 1: Competitor vs Your Brand analysis."""
    brand_overview: str = Field(..., description="Overview of the analyzed brand")
    business_category: str = Field(..., description="Main business category")
    main_products_services: list[str] = Field(default_factory=list, description="Main products and services")
    your_brand: Optional[BrandProfile] = Field(
        None, description="Your brand's side of the comparison table (same fields as each competitor)"
    )
    competitors: list[Competitor] = Field(default_factory=list, min_length=3, description="Identified competitor suggestions (minimum 3)")
    brand_strengths: list[str] = Field(default_factory=list, description="Your brand's competitive advantages")
    opportunities: list[str] = Field(default_factory=list, description="Opportunities to improve market positioning")


# ── Target Search Queries ────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    """A single target search query."""
    query: str = Field("", description="The search query string")
    platforms: list[Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]] = Field(
        default_factory=list, min_length=1, max_length=1,
        description="The primary platform for this query: Google, Facebook, Instagram, LinkedIn, or X",
    )
    intent: str = Field("", description="Search intent category")
    business_relevance: str = Field("", description="Why this query is relevant to the business")
    target_audience: str = Field("", description="Who would use this search query")


# ── SEO Improvements ────────────────────────────────────────────────────────

class SupportingContent(BaseModel):
    """A suggested piece of supporting content."""
    content_type: str = Field("", description="Type of content (e.g., blog post, landing page, FAQ)")
    title: str = Field("", description="Suggested title")
    description: str = Field("", description="Brief description of the content")
    target_keyword: str = Field("", description="Target keyword for this content")


class SEOImprovements(BaseModel):
    """Section 3: SEO improvement recommendations."""
    primary_keyword: str = Field("", description="Recommended primary keyword")
    secondary_keywords: list[str] = Field(default_factory=list, description="Recommended secondary keywords")
    long_tail_keywords: list[str] = Field(default_factory=list, description="Recommended long-tail keywords")
    business_keywords: list[str] = Field(default_factory=list, description="Relevant business keywords")
    recommended_title: str = Field("", description="Recommended SEO title")
    title_primary_keyword: str = Field("", description="Primary keyword used in the title")
    title_structure_notes: str = Field("", description="Notes on title structure improvement")
    meta_description: str = Field("", description="Recommended meta description")
    business_summary: str = Field("", description="Short, human-friendly business summary")
    meta_keywords: list[str] = Field(default_factory=list, description="Relevant keywords for meta description")
    supporting_content: list[SupportingContent] = Field(min_length=3, description="At least three suggested supporting content ideas")


# ── Top Services ─────────────────────────────────────────────────────────────

class Service(BaseModel):
    """A single identified service."""
    service_name: str = Field("", description="Name of the service")
    description: str = Field("", description="Short service explanation")
    target_industry: str = Field("", description="Relevant business industry")
    target_customer: str = Field("", description="Potential customer type")
    main_benefit: str = Field("", description="Why customers need this service")
    source: Literal["website", "inferred"] = Field(
        "inferred", description="'website' if explicitly supported by page text; otherwise 'inferred'"
    )


# ── Target Audience ──────────────────────────────────────────────────────────

class AudienceSegment(BaseModel):
    """A single audience segment."""
    audience_name: str = Field(..., description="Audience segment name")
    business_type: str = Field(..., description="Type of business in this segment")
    requirement: str = Field(..., description="Primary requirement or need")


class TargetAudience(BaseModel):
    """Section 5: Target audience identification."""
    primary_audience: list[AudienceSegment] = Field(default_factory=list, description="Primary target audiences")
    secondary_audience: list[AudienceSegment] = Field(default_factory=list, description="Secondary target audiences")
    industries: list[str] = Field(default_factory=list, description="Relevant industry segments")
    business_types: list[str] = Field(default_factory=list, description="Types of businesses / buyers served")
    customer_profiles: list[str] = Field(default_factory=list, description="Short ideal-customer profiles")
    customer_needs: list[str] = Field(default_factory=list, description="Customer needs and challenges")
    geographical_focus: Optional[str] = Field(None, description="Location or geographical focus if available")
    customer_interests: list[str] = Field(default_factory=list, description="Potential customer interests")
    recommended_segments: list[str] = Field(default_factory=list, description="Recommended audience segments for marketing")


# ── Full Analysis ────────────────────────────────────────────────────────────

class Analysis(BaseModel):
    """All five analysis sections combined."""
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEOImprovements
    top_services: list[Service] = Field(min_length=5, max_length=5)
    target_audience: TargetAudience


class BrandInfo(BaseModel):
    """Extracted brand information."""
    name: str = Field(..., description="Brand name")
    category: str = Field(..., description="Business category")
    summary: str = Field(..., description="Short business summary")


class LinkAnalysisResponse(BaseModel):
    """Complete response from the link-analysis endpoint."""
    success: bool = True
    website: str = Field(..., description="The analyzed website URL")
    brand: BrandInfo
    analysis: Analysis


# ── Error ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error description")
