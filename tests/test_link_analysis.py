import copy
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Shared mock LLM response ──────────────────────────────────────────────────

MOCK_LLM_RESPONSE = {
    "brand": {
        "name": "Test Corp",
        "category": "Technology",
        "summary": "A test technology company.",
    },
    "analysis": {
        "competitor_analysis": {
            "brand_overview": "Test Corp is a technology company.",
            "business_category": "Technology",
            "main_products_services": ["Web Dev", "Mobile Apps"],
            "competitors": [
                {
                    "name": "Rival Inc",
                    "main_service": "Web Development",
                    "target_market": "SMBs",
                    "key_strength": "Established brand",
                    "weakness_or_gap": "High pricing",
                    "opportunity": "Offer competitive pricing",
                    "competitor_source": "AI-identified based on industry knowledge",
                },
                {
                    "name": "Acme Digital",
                    "main_service": "Mobile Apps",
                    "target_market": "Startups",
                    "key_strength": "Fast delivery",
                    "weakness_or_gap": "Limited support",
                    "opportunity": "Provide better after-sales support",
                    "competitor_source": "AI-identified based on industry knowledge",
                },
                {
                    "name": "TechPro",
                    "main_service": "Cloud Services",
                    "target_market": "Enterprises",
                    "key_strength": "Scalability",
                    "weakness_or_gap": "Complex UX",
                    "opportunity": "Simplify onboarding",
                    "competitor_source": "AI-identified based on industry knowledge",
                },
            ],
            "brand_strengths": ["Innovative", "Cost-effective"],
            "opportunities": ["Expand to new markets"],
        },
        "target_search_queries": [
            {
                "query": "web development services",
                "platforms": ["Google"],
                "intent": "Service Search",
                "business_relevance": "Core service",
                "target_audience": "Business owners",
            },
            {
                "query": "mobile app development company",
                "platforms": ["Facebook"],
                "intent": "Business Discovery",
                "business_relevance": "Mobile services",
                "target_audience": "Startup founders",
            },
            {
                "query": "web design inspiration 2025",
                "platforms": ["Instagram"],
                "intent": "Inspiration",
                "business_relevance": "Design showcase",
                "target_audience": "Designers",
            },
            {
                "query": "enterprise web development",
                "platforms": ["LinkedIn"],
                "intent": "B2B Search",
                "business_relevance": "Enterprise sales",
                "target_audience": "CTOs",
            },
            {
                "query": "latest web trends",
                "platforms": ["X"],
                "intent": "Service Discovery",
                "business_relevance": "Thought leadership",
                "target_audience": "Tech enthusiasts",
            },
        ],
        "seo_improvements": {
            "primary_keyword": "web development",
            "secondary_keywords": ["website design", "mobile apps"],
            "long_tail_keywords": ["affordable web development for startups"],
            "business_keywords": ["technology services"],
            "recommended_title": "Test Corp | Web Development & Mobile Apps",
            "title_primary_keyword": "web development",
            "title_structure_notes": "Brand + primary service",
            "meta_description": "Test Corp provides affordable web development and mobile app solutions.",
            "business_summary": "Affordable tech solutions for businesses.",
            "meta_keywords": ["web development", "mobile apps"],
            "supporting_content": [
                {
                    "content_type": "blog post",
                    "title": "Top 10 Web Design Trends",
                    "description": "A guide to modern web design trends.",
                    "target_keyword": "web design trends",
                },
                {
                    "content_type": "landing page",
                    "title": "Mobile App Development Services",
                    "description": "Custom mobile apps for your business.",
                    "target_keyword": "mobile app development",
                },
                {
                    "content_type": "FAQ",
                    "title": "Web Development FAQ",
                    "description": "Common questions about our web services.",
                    "target_keyword": "web development FAQ",
                },
            ],
        },
        "top_services": [
            {
                "service_name": "Web Development",
                "description": "Custom website development.",
                "target_industry": "Technology",
                "target_customer": "SMBs",
                "main_benefit": "Online presence",
                "source": "website",
            },
            {
                "service_name": "Mobile Apps",
                "description": "iOS and Android app development.",
                "target_industry": "Technology",
                "target_customer": "Startups",
                "main_benefit": "Mobile reach",
                "source": "website",
            },
            {
                "service_name": "SEO Services",
                "description": "Search engine optimization.",
                "target_industry": "Marketing",
                "target_customer": "Business owners",
                "main_benefit": "Organic traffic",
                "source": "inferred",
            },
            {
                "service_name": "UI/UX Design",
                "description": "User interface design.",
                "target_industry": "Technology",
                "target_customer": "Product teams",
                "main_benefit": "Better UX",
                "source": "website",
            },
            {
                "service_name": "Cloud Hosting",
                "description": "Managed hosting solutions.",
                "target_industry": "Technology",
                "target_customer": "Enterprises",
                "main_benefit": "Reliability",
                "source": "inferred",
            },
        ],
        "target_audience": {
            "primary_audience": [
                {"audience_name": "SMBs", "business_type": "Small Business", "requirement": "Websites"}
            ],
            "secondary_audience": [
                {"audience_name": "Startups", "business_type": "Startup", "requirement": "MVPs"}
            ],
            "industries": ["Technology", "Retail"],
            "customer_needs": ["Online presence", "Mobile apps"],
            "geographical_focus": "Global",
            "customer_interests": ["Digital transformation"],
            "recommended_segments": ["E-commerce businesses"],
        },
    },
}

MOCK_WEBSITE_CONTENT = {
    "url": "https://example.com",
    "title": "Test Corp",
    "meta_description": "A test company.",
    "meta_keywords": "test, technology",
    "headings": [{"level": 1, "text": "Welcome"}],
    "main_text": "Test Corp is a technology company.",
    "navigation_links": ["Home", "About", "Services"],
    "image_alt_texts": ["team photo"],
}


# ── Helper ────────────────────────────────────────────────────────────────────

def _patched_analysis(extractor_return=None, llm_return=None):
    """
    Context manager that patches both WebsiteExtractor and LLMService.
    Returns the response from POST /link-analysis for https://example.com.
    """
    extractor_return = extractor_return or MOCK_WEBSITE_CONTENT
    llm_return = llm_return if llm_return is not None else MOCK_LLM_RESPONSE

    with patch("app.services.analysis_service.WebsiteExtractor") as MockExtractor, \
         patch("app.services.analysis_service.LLMService") as MockLLM, \
         patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None), \
         patch("app.services.analysis_service.analysis_cache.set", new_callable=AsyncMock):

        MockExtractor.return_value.extract = AsyncMock(return_value=extractor_return)
        MockLLM.return_value.analyze = AsyncMock(return_value=llm_return)
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    return response


# ── Health Check ──────────────────────────────────────────────────────────────

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_reports_config_without_leaking_key():
    """JSON health includes readiness details but never the API key itself."""
    data = client.get("/health").json()
    assert set(data) >= {"llm_model", "llm_api_key_configured", "cached_analyses", "uptime_seconds"}
    assert isinstance(data["llm_api_key_configured"], bool)
    from app.config import settings
    if settings.GEMINI_API_KEY:
        assert settings.GEMINI_API_KEY not in client.get("/health").text


def test_health_in_browser_returns_status_page():
    """Browsers asking for HTML get the readable status page, not raw JSON."""
    response = client.get("/health", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Service Status" in response.text


def test_docs_page_links_back_to_ui():
    """Swagger docs still load and include a way back to the web UI."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert 'href="/"' in response.text
    assert client.get("/openapi.json").json()["paths"].get("/link-analysis")


def test_web_ui_served_at_root():
    """The browser UI is served at / and posts to the analysis endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/link-analysis" in response.text


# ── Input Validation ──────────────────────────────────────────────────────────

def test_missing_url():
    """Test that a missing URL returns a 422 validation error."""
    response = client.post("/link-analysis", json={})
    assert response.status_code == 422


def test_invalid_url():
    """Test that an invalid URL returns a 422 error."""
    response = client.post("/link-analysis", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_private_ip_blocked():
    """Test that localhost / private IPs are blocked (SSRF protection)."""
    response = client.post("/link-analysis", json={"url": "http://127.0.0.1"})
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "security" in detail or "blocked" in detail


def test_private_ip_10_blocked():
    """Test that 10.x.x.x IPs are blocked."""
    response = client.post("/link-analysis", json={"url": "http://10.0.0.1"})
    assert response.status_code == 400


# ── URL Validator Unit Tests ──────────────────────────────────────────────────

from app.utils.validators import validate_url, SSRFError, URLValidationError


def test_validate_url_good():
    """A valid public URL should pass."""
    result = validate_url("https://www.google.com")
    assert result == "https://www.google.com"


def test_validate_url_ftp_rejected():
    """FTP URLs should be rejected."""
    with pytest.raises(URLValidationError):
        validate_url("ftp://files.example.com/data")


def test_validate_url_localhost_ssrf():
    """Localhost should trigger SSRF error."""
    with pytest.raises(SSRFError):
        validate_url("http://localhost/admin")


def test_validate_url_192_168_ssrf():
    """192.168.x.x should trigger SSRF error."""
    with pytest.raises(SSRFError):
        validate_url("http://192.168.1.1")


def test_validate_url_no_host():
    """A URL with no host should be rejected."""
    with pytest.raises(URLValidationError):
        validate_url("http://")


def test_validate_url_with_credentials_rejected():
    """URLs with embedded credentials should be rejected."""
    with pytest.raises(URLValidationError):
        validate_url("http://user:pass@example.com")


def test_validate_url_non_standard_port_rejected():
    """Non-standard ports should be rejected."""
    with pytest.raises(URLValidationError):
        validate_url("http://example.com:8080/path")


# ── Mocked Full Analysis (happy path) ────────────────────────────────────────

@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_full_analysis_mocked(MockExtractor, MockLLM):
    """Test the full analysis pipeline with mocked extractor and LLM."""
    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None), \
         patch("app.services.analysis_service.analysis_cache.set", new_callable=AsyncMock):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["website"] in ("https://example.com", "https://example.com/")
    assert data["brand"]["name"] == "Test Corp"
    assert len(data["analysis"]["competitor_analysis"]["competitors"]) == 3
    assert len(data["analysis"]["target_search_queries"]) == 5
    assert len(data["analysis"]["top_services"]) == 5
    assert data["analysis"]["seo_improvements"]["primary_keyword"] == "web development"
    assert len(data["analysis"]["seo_improvements"]["supporting_content"]) >= 3


# ── LLM Failure → 502 ────────────────────────────────────────────────────────

@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_llm_runtime_error_returns_502(MockExtractor, MockLLM):
    """A RuntimeError from the LLM should surface as HTTP 502."""
    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(side_effect=RuntimeError("LLM API error (500)"))

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502


# ── AnalysisOutputError paths → 502 ──────────────────────────────────────────

@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_too_few_competitors_returns_502(MockExtractor, MockLLM):
    """Fewer than 3 competitors from LLM should return 502."""
    bad_response = copy.deepcopy(MOCK_LLM_RESPONSE)
    bad_response["analysis"]["competitor_analysis"]["competitors"] = \
        bad_response["analysis"]["competitor_analysis"]["competitors"][:1]  # only 1

    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=bad_response)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert "competitor" in response.json()["detail"].lower()


@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_too_many_competitors_returns_502(MockExtractor, MockLLM):
    """More than 3 competitors from LLM should return 502 (prompt says exactly 3)."""
    bad_response = copy.deepcopy(MOCK_LLM_RESPONSE)
    extra = copy.deepcopy(bad_response["analysis"]["competitor_analysis"]["competitors"][0])
    extra["name"] = "Extra Corp"
    bad_response["analysis"]["competitor_analysis"]["competitors"].append(extra)  # now 4

    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=bad_response)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert "competitor" in response.json()["detail"].lower()


@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_wrong_query_count_returns_502(MockExtractor, MockLLM):
    """Wrong number of search queries from LLM should return 502."""
    bad_response = copy.deepcopy(MOCK_LLM_RESPONSE)
    bad_response["analysis"]["target_search_queries"] = \
        bad_response["analysis"]["target_search_queries"][:2]  # only 2

    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=bad_response)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert "search quer" in response.json()["detail"].lower()


@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_wrong_service_count_returns_502(MockExtractor, MockLLM):
    """Wrong number of top services from LLM should return 502."""
    bad_response = copy.deepcopy(MOCK_LLM_RESPONSE)
    bad_response["analysis"]["top_services"] = \
        bad_response["analysis"]["top_services"][:3]  # only 3

    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=bad_response)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert "service" in response.json()["detail"].lower()


@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_insufficient_supporting_content_returns_502(MockExtractor, MockLLM):
    """Fewer than 3 supporting content items from LLM should return 502."""
    bad_response = copy.deepcopy(MOCK_LLM_RESPONSE)
    bad_response["analysis"]["seo_improvements"]["supporting_content"] = \
        bad_response["analysis"]["seo_improvements"]["supporting_content"][:1]  # only 1

    MockExtractor.return_value.extract = AsyncMock(return_value=MOCK_WEBSITE_CONTENT)
    MockLLM.return_value.analyze = AsyncMock(return_value=bad_response)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 502
    assert "supporting content" in response.json()["detail"].lower()


# ── Caching ───────────────────────────────────────────────────────────────────

@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_cache_hit_skips_extractor_and_llm(MockExtractor, MockLLM):
    """
    When the cache already holds a result, neither the extractor nor the LLM
    should be called.
    """
    from app.schemas import LinkAnalysisResponse, BrandInfo, Analysis, \
        CompetitorAnalysis, Competitor, SearchQuery, SEOImprovements, \
        SupportingContent, Service, TargetAudience, AudienceSegment

    # Build a minimal cached response object
    cached_result = LinkAnalysisResponse(
        success=True,
        website="https://example.com/",
        brand=BrandInfo(name="Cached Corp", category="Tech", summary="Cached."),
        analysis=Analysis(
            competitor_analysis=CompetitorAnalysis(
                brand_overview="Cached",
                business_category="Tech",
                main_products_services=[],
                competitors=[
                    Competitor(name=f"C{i}", competitor_source="AI-identified based on industry knowledge")
                    for i in range(3)
                ],
                brand_strengths=[],
                opportunities=[],
            ),
            target_search_queries=[
                SearchQuery(query=f"q{i}", platforms=["Google"])
                for i in range(5)
            ],
            seo_improvements=SEOImprovements(
                primary_keyword="cached",
                supporting_content=[
                    SupportingContent() for _ in range(3)
                ],
            ),
            top_services=[Service(service_name=f"S{i}") for i in range(5)],
            target_audience=TargetAudience(),
        ),
    )

    with patch("app.services.analysis_service.analysis_cache.get",
               new_callable=AsyncMock, return_value=cached_result):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 200
    assert response.json()["brand"]["name"] == "Cached Corp"
    # Extractor and LLM must not have been called
    MockExtractor.return_value.extract.assert_not_called()
    MockLLM.return_value.analyze.assert_not_called()


# ── Website inaccessible → 400 ────────────────────────────────────────────────

@patch("app.services.analysis_service.LLMService")
@patch("app.services.analysis_service.WebsiteExtractor")
def test_website_inaccessible_returns_400(MockExtractor, MockLLM):
    """A ConnectionError from the extractor should surface as HTTP 400."""
    MockExtractor.return_value.extract = AsyncMock(
        side_effect=ConnectionError("Could not safely fetch the website")
    )
    MockLLM.return_value.analyze = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    with patch("app.services.analysis_service.analysis_cache.get", new_callable=AsyncMock, return_value=None):
        response = client.post("/link-analysis", json={"url": "https://example.com"})

    assert response.status_code == 400
    assert "website" in response.json()["detail"].lower()


# ── Rate Limiting ─────────────────────────────────────────────────────────────

def test_rate_limit_returns_429():
    """
    Exceeding the configured rate limit should return HTTP 429.

    Exercises the pure-ASGI _RateLimitMiddleware directly with two back-to-back
    requests from the same IP, with a limit of 1 call per window.
    """
    import asyncio
    from app.main import _RateLimitMiddleware

    received_statuses = []

    async def fake_app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-length", b"2")],
        })
        await send({"type": "http.response.body", "body": b"ok"})

    async def fake_send(event):
        if event["type"] == "http.response.start":
            received_statuses.append(event["status"])

    mw = _RateLimitMiddleware(fake_app, calls=1, period=60)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "client": ("1.2.3.4", 12345),
        "headers": [],
    }

    async def run():
        await mw(scope, None, fake_send)   # 1st request — should pass
        await mw(scope, None, fake_send)   # 2nd request — should be blocked

    asyncio.run(run())

    assert received_statuses[0] == 200
    assert received_statuses[1] == 429


# ── CacheService unit tests ───────────────────────────────────────────────────

import asyncio as _asyncio


def test_cache_set_and_get():
    """CacheService.get returns the stored value."""
    from app.services.cache_service import CacheService

    cache = CacheService(ttl_seconds=60)

    async def _run():
        await cache.set("https://example.com", {"result": 1})
        return await cache.get("https://example.com")

    result = _asyncio.run(_run())
    assert result == {"result": 1}


def test_cache_expired_entry_returns_none():
    """CacheService.get returns None for an expired entry."""
    from app.services.cache_service import CacheService

    cache = CacheService(ttl_seconds=0)  # expires immediately

    async def _run():
        await cache.set("https://example.com", {"result": 2})
        # Force expiry by setting TTL to 0 — entry should already be expired
        import time
        entry = cache._store.get(cache._normalise("https://example.com"))
        if entry:
            # Manually backdate expiry
            cache._store[cache._normalise("https://example.com")] = (entry[0], time.monotonic() - 1)
        return await cache.get("https://example.com")

    result = _asyncio.run(_run())
    assert result is None


def test_cache_normalises_trailing_slash():
    """URLs with and without trailing slashes should share the same cache key."""
    from app.services.cache_service import CacheService

    cache = CacheService(ttl_seconds=60)

    async def _run():
        await cache.set("https://example.com/", {"v": 42})
        return await cache.get("https://example.com")

    result = _asyncio.run(_run())
    assert result == {"v": 42}


def test_cache_invalidate():
    """CacheService.invalidate removes the entry and returns True."""
    from app.services.cache_service import CacheService

    cache = CacheService(ttl_seconds=60)

    async def _run():
        await cache.set("https://example.com", {"v": 1})
        removed = await cache.invalidate("https://example.com")
        after = await cache.get("https://example.com")
        return removed, after

    removed, after = _asyncio.run(_run())
    assert removed is True
    assert after is None


# ── Section 1 / Section 5 extra fields ───────────────────────────────────────

def test_your_brand_and_audience_profile_fields_pass_through():
    """'Your Brand' comparison row and audience business types/profiles are returned."""
    llm = copy.deepcopy(MOCK_LLM_RESPONSE)
    llm["analysis"]["competitor_analysis"]["your_brand"] = {
        "name": "Test Corp",
        "main_service": "Web Development",
        "target_market": "Small Businesses",
        "key_strength": "Affordable Solutions",
        "opportunity": "Improve Online Visibility",
    }
    llm["analysis"]["target_audience"]["business_types"] = ["Startups", "Retail"]
    llm["analysis"]["target_audience"]["customer_profiles"] = ["Founder of a 10-person SaaS"]

    response = _patched_analysis(llm_return=llm)

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["competitor_analysis"]["your_brand"]["target_market"] == "Small Businesses"
    assert analysis["target_audience"]["business_types"] == ["Startups", "Retail"]
    assert analysis["target_audience"]["customer_profiles"] == ["Founder of a 10-person SaaS"]


# ── Content extraction ───────────────────────────────────────────────────────

def test_extract_content_does_not_duplicate_nested_text():
    """Wrapper <div>s must not repeat their children's text in main_text."""
    from app.services.website_extractor import WebsiteExtractor

    html = """
    <html><head><title>Acme</title><script>var x = 1;</script></head><body>
      <div class="wrap">
        <div class="hero"><h1>Acme</h1><p>We build fast websites for small businesses.</p></div>
        <div class="services"><ul>
          <li><span>Web development for startups and SMBs</span></li>
          <li><p>SEO audits and content strategy plans</p></li>
        </ul></div>
        <div>Contact our London office for a free quote today</div>
      </div>
    </body></html>
    """
    content = WebsiteExtractor().extract_content(html)
    lines = content["main_text"].splitlines()

    assert lines == [
        "We build fast websites for small businesses.",
        "Web development for startups and SMBs",
        "SEO audits and content strategy plans",
        "Contact our London office for a free quote today",
    ]
    assert "var x" not in content["main_text"]
    assert content["title"] == "Acme"
    assert {"level": 1, "text": "Acme"} in content["headings"]
