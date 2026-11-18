"""
Live end-to-end benchmark and verification against a real website.

Tests the full AnalysisService pipeline:
1. Cold run: URL validation -> SSRF safe fetching -> BS4 content cleaning
   -> Google Gemini API -> Pydantic response assembly -> Competitor enrichment
   -> In-memory cache storage.
2. Warm run: Verifies in-memory cache hit on the normalized URL and measures
   exact repeat request latency.
3. Records actual token counts reported by Gemini API and calculates actual cost.
"""
import asyncio
import json
import logging
import sys
import time

sys.path.insert(0, ".")

from app.services.analysis_service import AnalysisService
from app.services.cache_service import analysis_cache

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def run(url: str = "https://stripe.com"):
    print("=" * 70)
    print(f"LIVE RUN & BENCHMARK AUDIT: {url}")
    print("=" * 70)

    # Pre-clear cache so cold run is strictly cold
    await analysis_cache.clear()

    # Step 1: Execute cold run via AnalysisService
    print("\n--- STEP 1: COLD RUN (FULL ANALYSIS PIPELINE) ---")
    service = AnalysisService()
    t_cold_start = time.monotonic()
    cold_response = await service.analyze(url)
    t_cold_end = time.monotonic()
    cold_duration = t_cold_end - t_cold_start

    # Retrieve extraction stats
    stats = getattr(service.extractor, "last_stats", {})
    raw_html_bytes = stats.get("raw_bytes", 0)
    raw_html_chars = stats.get("raw_chars", 0)
    cleaned_chars = stats.get("cleaned_chars", 0)
    reduction_pct = (1.0 - (cleaned_chars / max(raw_html_chars, 1))) * 100 if raw_html_chars else 0

    print(f"  Raw HTML Size        : {raw_html_bytes:,} bytes ({raw_html_chars:,} chars)")
    print(f"  Cleaned Text Size    : {cleaned_chars:,} chars")
    print(f"  Extraction Reduction : {reduction_pct:.1f}% reduction from raw HTML")
    print(f"  Cold Run Duration    : {cold_duration:.2f}s")

    # Retrieve Gemini token usage metadata from LLMService instance
    usage = getattr(service.llm, "last_usage", {})
    prompt_tokens = usage.get("promptTokenCount", 0)
    candidate_tokens = usage.get("candidatesTokenCount", 0)
    total_tokens = usage.get("totalTokenCount", 0)

    # Cost calculation using official Gemini 3.5 Flash-Lite rates:
    # $0.30 per 1M input tokens, $2.50 per 1M output tokens
    cost_input = (prompt_tokens / 1_000_000) * 0.30
    cost_output = (candidate_tokens / 1_000_000) * 2.50
    total_cost = cost_input + cost_output

    print(f"  Gemini Prompt Tokens : {prompt_tokens:,}")
    print(f"  Gemini Output Tokens : {candidate_tokens:,}")
    print(f"  Gemini Total Tokens  : {total_tokens:,}")
    print(f"  Calculated Call Cost : ${total_cost:.6f} USD")

    # Step 2: Execute warm run via AnalysisService (Cache Hit)
    print("\n--- STEP 2: WARM RUN (CACHE HIT VERIFICATION) ---")
    t_warm_start = time.monotonic()
    warm_response = await service.analyze(url)
    t_warm_end = time.monotonic()
    warm_duration = t_warm_end - t_warm_start

    print(f"  Warm Run Duration    : {warm_duration * 1000:.3f} ms ({warm_duration:.4f}s)")
    print(f"  Cache Integrity Check: {'PASSED' if cold_response.model_dump() == warm_response.model_dump() else 'FAILED'}")

    # Step 3: Print summary of extracted business intelligence
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"Brand: {cold_response.brand.name} ({cold_response.brand.category})")
    print(f"Summary: {cold_response.brand.summary}\n")

    print(f"Competitors ({len(cold_response.analysis.competitor_analysis.competitors)} returned):")
    for comp in cold_response.analysis.competitor_analysis.competitors:
        print(f"  - {comp.name} [{comp.competitor_source}]")
        print(f"    Strength: {comp.key_strength}")
        print(f"    Opportunity: {comp.opportunity}")

    print(f"\nTop Services ({len(cold_response.analysis.top_services)} returned):")
    for svc in cold_response.analysis.top_services:
        print(f"  - [{svc.source:7s}] {svc.service_name}: {svc.main_benefit}")

    print(f"\nTarget Search Queries ({len(cold_response.analysis.target_search_queries)} returned):")
    for q in cold_response.analysis.target_search_queries:
        print(f"  - [{q.platforms[0]:9s}] {q.query} ({q.intent})")

    print(f"\nSEO Improvements:")
    seo = cold_response.analysis.seo_improvements
    print(f"  Primary Keyword  : {seo.primary_keyword}")
    print(f"  Recommended Title: {seo.recommended_title}")
    print(f"  Meta Description : {seo.meta_description}")

    # Output JSON file with embedded benchmark metadata
    output_dict = cold_response.model_dump()
    output_dict["_benchmark_metadata"] = {
        "target_url": url,
        "raw_html_bytes": raw_html_bytes,
        "raw_html_chars": raw_html_chars,
        "cleaned_text_chars": cleaned_chars,
        "content_reduction_percent": round(reduction_pct, 2),
        "cold_run_seconds": round(cold_duration, 3),
        "warm_cache_hit_ms": round(warm_duration * 1000, 3),
        "prompt_tokens": prompt_tokens,
        "candidates_tokens": candidate_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(total_cost, 6),
    }

    with open("live_run_output.json", "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("Artifacts generated:")
    print("  - live_run_output.json (structured output + real benchmark metadata)")
    print("=" * 70)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    asyncio.run(run(target))
