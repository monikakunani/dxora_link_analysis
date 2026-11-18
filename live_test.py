"""Live end-to-end test against a real website using the actual Gemini API key."""
import asyncio
import json
import sys
import time

sys.path.insert(0, ".")

from app.services.website_extractor import WebsiteExtractor
from app.services.llm_service import LLMService
from app.services.analysis_service import AnalysisService


async def run(url: str = "https://stripe.com"):
    print(f"\nTarget URL : {url}")
    print("-" * 60)
    t0 = time.monotonic()

    extractor = WebsiteExtractor()
    print("Step 1 — Fetching website content...")
    content = await extractor.extract(url)
    t1 = time.monotonic()
    print(f"           Done in {t1 - t0:.1f}s — {len(content['main_text'])} chars extracted")

    print("Step 2 — Calling Gemini API...")
    llm = LLMService()
    raw = await llm.analyze(content)
    t2 = time.monotonic()
    print(f"           Done in {t2 - t1:.1f}s")

    print("Step 3 — Building validated response...")
    svc = AnalysisService()
    result = svc._build_response(url, raw)
    t3 = time.monotonic()
    print(f"           Done in {t3 - t2:.2f}s")

    total = t3 - t0
    llm_time = t2 - t1
    extract_time = t1 - t0

    print()
    print("=" * 60)
    print("BRAND")
    print("=" * 60)
    print(f"  Name     : {result.brand.name}")
    print(f"  Category : {result.brand.category}")
    print(f"  Summary  : {result.brand.summary}")

    print()
    print("=" * 60)
    print("COMPETITORS  (source: AI-identified based on industry knowledge)")
    print("=" * 60)
    for c in result.analysis.competitor_analysis.competitors:
        print(f"  • {c.name}")
        print(f"    Service   : {c.main_service}")
        print(f"    Strength  : {c.key_strength}")
        print(f"    Weakness  : {c.weakness_or_gap}")
        print(f"    Opportunity: {c.opportunity}")

    print()
    print("=" * 60)
    print("TOP SERVICES")
    print("=" * 60)
    for s in result.analysis.top_services:
        print(f"  [{s.source:8s}] {s.service_name}: {s.description}")

    print()
    print("=" * 60)
    print("TARGET SEARCH QUERIES")
    print("=" * 60)
    for q in result.analysis.target_search_queries:
        print(f"  {q.platforms[0]:12s} | {q.query}")
        print(f"               intent: {q.intent}")

    print()
    print("=" * 60)
    print("SEO IMPROVEMENTS")
    print("=" * 60)
    seo = result.analysis.seo_improvements
    print(f"  Primary keyword  : {seo.primary_keyword}")
    print(f"  Recommended title: {seo.recommended_title}")
    print(f"  Meta description : {seo.meta_description}")
    print(f"  Secondary keywords: {', '.join(seo.secondary_keywords[:5])}")
    print(f"  Supporting content suggestions: {len(seo.supporting_content)}")
    for sc in seo.supporting_content:
        print(f"    - [{sc.content_type}] {sc.title}")

    print()
    print("=" * 60)
    print("TARGET AUDIENCE")
    print("=" * 60)
    ta = result.analysis.target_audience
    print("  Primary:")
    for a in ta.primary_audience:
        print(f"    • {a.audience_name} ({a.business_type}): {a.requirement}")
    print("  Secondary:")
    for a in ta.secondary_audience:
        print(f"    • {a.audience_name} ({a.business_type}): {a.requirement}")
    print(f"  Geo focus: {ta.geographical_focus}")
    print(f"  Industries: {', '.join(ta.industries)}")

    print()
    print("=" * 60)
    print("PERFORMANCE")
    print("=" * 60)
    print(f"  Website extraction : {extract_time:.1f}s")
    print(f"  Gemini API call    : {llm_time:.1f}s")
    print(f"  Total end-to-end   : {total:.1f}s")

    # Save full JSON output
    out_path = "live_run_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\nFull JSON saved to {out_path}")
    return total, extract_time, llm_time


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    asyncio.run(run(url))
