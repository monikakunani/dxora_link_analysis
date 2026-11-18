# AI-Powered Website Link Analysis API

> A production-grade FastAPI microservice that extracts website content, conducts structured brand and competitive analysis via Google Gemini LLM, and produces validated SEO, service, and audience intelligence.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![LLM](https://img.shields.io/badge/LLM-Gemini_3.5_Flash--Lite-orange)
![Tests](https://img.shields.io/badge/Tests-26%2F26%20Passing-brightgreen)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
- [Live Benchmark & Measured Run Verification](#live-benchmark--measured-run-verification)
- [Sample API Request & Response](#sample-api-request--response)
- [Running Tests](#running-tests)
- [LLM Platform Comparison & Recommendation](#llm-platform-comparison--recommendation)
- [Cost Optimization Strategies](#cost-optimization-strategies)
- [Competitor Intelligence & Sourcing](#competitor-intelligence--sourcing)
- [Error Handling](#error-handling)
- [Security](#security)
- [Submission & Verification Checklist](#submission--verification-checklist)

---

## Features

- **SSRF-Safe Content Extraction**: Fetches and parses website HTML using `aiohttp` + `BeautifulSoup4` with DNS pinning, manual redirect verification, and a 5 MB streaming cap.
- **LLM-Powered Business Intelligence**: Uses Google Gemini (`gemini-3.5-flash-lite`) to analyze page context in a single cost-optimized prompt.
- **5-Section Structured Analysis**:
  1. **Competitor vs Your Brand Analysis**: Pinpoints brand strengths, opportunities, and exactly 3 market competitors with transparent sourcing labels (`competitor_source: "AI-identified based on industry knowledge"`).
  2. **Top 5 Target Search Queries**: Generates exactly 5 queries tailored to 5 major platforms (Google, Facebook, Instagram, LinkedIn, X).
  3. **SEO Improvement Recommendations**: Primary, secondary, long-tail keywords, title tag, meta description, and 3+ supporting content recommendations.
  4. **Top 5 Services Identification**: Exactly 5 key services labeled as explicitly mentioned (`website`) or recommended (`inferred`).
  5. **Target Audience Identification**: Primary & secondary audience segments, user needs, and relevant industries.
- **In-Memory TTL Caching**: Eliminates duplicate LLM calls on repeated URLs using normalized URL keys.
- **Pure-ASGI Sliding-Window Rate Limiting**: Protects upstream LLM quotas per client IP (default: 60 req/min).
- **Strict Pydantic Validation**: Enforces exact required counts (3 competitors, 5 search queries, 5 services, 3+ content pieces) at the API boundary.

---

## Architecture

```text
+-------------------+       +--------------------+       +----------------------+       +--------------+
|      Client       | ----> |   FastAPI Server   | ----> |   WebsiteExtractor   | ----> |  Target URL  |
|  (POST /link-     |       |  (Rate Limit +     |       |   (aiohttp + BS4)    |       |              |
|   analysis)       | <---- |   SSRF Validation) |       +----------------------+       +--------------+
+-------------------+       +--------------------+                  |
                                     |                              v
                                     |                   +----------------------+
                                     |                   |      LLMService      |
                                     |                   |     (Gemini API)     |
                                     |                   +----------------------+
                                     |                              |
                                     v                              v
                            +--------------------+       +----------------------+
                            |    CacheService    | <---> |   AnalysisService    |
                            |  (In-memory TTL)   |       | (Orchestration &     |
                            +--------------------+       |  Competitor Enforce) |
                                                         +----------------------+
                                                                    |
                                                                    v
                                                         +----------------------+
                                                         |  CompetitorService   |
                                                         |  (Enrichment Hook)   |
                                                         +----------------------+
```

### Processing Flow:
1. Client submits target URL to `POST /link-analysis`.
2. IP checked against pure-ASGI sliding-window rate limiter.
3. Cache inspected for normalized URL key (`https://example.com/` matches `https://example.com`).
4. On cache miss, `validate_url` performs pre-flight SSRF protection (scheme, port, private IP ranges).
5. `WebsiteExtractor` fetches content using pinned DNS resolvers and manually audited redirects.
6. `BeautifulSoup4` cleans noise tags (`<script>`, `<style>`, SVGs) and extracts structured headings, links, and text capped at 50,000 characters.
7. `LLMService` submits content to Gemini with automatic exponential backoff retries for transient capacity errors (HTTP 429/503).
8. `AnalysisService` verifies item counts, invokes the `CompetitorService` enrichment hook, stores the result in cache, and returns the response.

---

## Project Structure

```text
dxora_link_analysis/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, routes, and ASGI rate limiter
│   ├── config.py                  # Pydantic/dotenv application settings
│   ├── schemas.py                 # Strict Pydantic response & request models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── website_extractor.py   # SSRF-safe HTML fetching & text cleaning
│   │   ├── llm_service.py         # Google Gemini API client with auto-retry
│   │   ├── analysis_service.py    # Pipeline orchestration & count enforcement
│   │   ├── cache_service.py       # TTL-based in-memory response cache
│   │   └── competitor_service.py  # Architectural hook for external competitor APIs
│   └── utils/
│       ├── __init__.py
│       └── validators.py          # Multi-layer SSRF prevention & URL sanitization
├── tests/
│   ├── __init__.py
│   └── test_link_analysis.py      # Full test suite (26/26 tests passing)
├── live_test.py                   # Script for live end-to-end verification
├── live_run_output.json           # Tracked raw JSON response with benchmark metadata
├── live_run.log                   # Tracked console execution log of real Gemini run
├── sample_response.json           # Illustrative reference fixture
├── Dockerfile                     # Multi-stage production container definition
├── .dockerignore                  # Docker build exclusion rules
├── .env.example                   # Environment variable template
├── requirements.txt               # Pinned Python package dependencies
├── pyproject.toml                 # Pytest configuration
└── README.md
```

---

## Setup & Installation

### Prerequisites

- **Python 3.10+** (tested on Python 3.13)
- **Google Gemini API Key** – Obtainable from [Google AI Studio](https://aistudio.google.com/apikey)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/dxora_link_analysis.git
cd dxora_link_analysis

# 2. Create and activate a virtual environment
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env

# 5. Set your Gemini API key in .env
# GEMINI_API_KEY=your_actual_api_key_here
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `LLM_MODEL` | `gemini-3.5-flash-lite` | Target Gemini model |
| `LLM_TIMEOUT` | `120` | LLM HTTP request timeout (seconds) |
| `REQUEST_TIMEOUT` | `60` | Website fetch timeout (seconds) |
| `MAX_CONTENT_LENGTH` | `50000` | Character cutoff for cleaned page content |
| `MAX_RESPONSE_BYTES` | `5242880` | Max decompressed HTML response size (5 MB) |
| `CACHE_TTL_SECONDS` | `3600` | In-memory cache duration for validated analyses |
| `RATE_LIMIT_CALLS` | `60` | Requests allowed per IP within the rate-limit window |
| `RATE_LIMIT_PERIOD` | `60` | Sliding window duration in seconds |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `4000` | Server bind port |

---

## Running the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The server will be reachable at `http://localhost:4000`.

### Docker Deployment

Build and run the self-contained container:

```bash
docker build -t dxora-link-analysis .
docker run --rm -p 4000:4000 --env-file .env dxora-link-analysis
```

The container runs as an unprivileged non-root user (`app`), incorporates an automated Docker health check against `GET /`, and excludes local environment secrets via `.dockerignore`.

---

## API Documentation

Interactive OpenAPI documentation is automatically served:

- **Swagger UI**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc**: [http://localhost:4000/redoc](http://localhost:4000/redoc)

---

## Live Benchmark & Measured Run Verification

A live end-to-end verification was executed against `https://stripe.com` through the full `AnalysisService` pipeline using the Google Gemini API (`gemini-3.5-flash-lite`).

Both execution artifacts are checked into the repository:
- Full output JSON with embedded benchmark metadata: [`live_run_output.json`](live_run_output.json)
- Full terminal execution log: [`live_run.log`](live_run.log)

### Measured Benchmark Data (Single Run on `https://stripe.com`)

| Metric | Measured Value | Measurement Basis |
|---|---|---|
| **Raw HTML Downloaded** | **724,310 bytes** (723,039 chars) | Live stream from `https://stripe.com` |
| **Cleaned Text Extracted** | **45,489 chars** | Post-BeautifulSoup script/style/SVG removal |
| **Content Reduction** | **93.7% reduction** | `(1 - 45,489 / 723,039) * 100` |
| **Gemini Prompt Tokens** | **11,669 tokens** | Reported by Gemini `usageMetadata.promptTokenCount` |
| **Gemini Output Tokens** | **2,326 tokens** | Reported by Gemini `usageMetadata.candidatesTokenCount` |
| **Gemini Total Tokens** | **13,995 tokens** | Reported by Gemini `usageMetadata.totalTokenCount` |
| **Calculated Inference Cost** | **$0.009316 USD** | Standard Gemini rates: `(11,669 * $0.30 + 2,326 * $2.50) / 1,000,000` |
| **Cold Run Latency** | **76.89s** | Includes 724 KB download + 2 transient 503 backoff retries (3s + 6s) + LLM inference |
| **Warm Cache Hit Latency** | **1.746 ms (0.0017s)** | Measured on repeat request to `AnalysisService.analyze()` |
| **Cache Output Parity** | **Identical (PASSED)** | Deep comparison of cold vs warm Pydantic response dictionaries |

---

## Sample API Request & Response

### Request

```bash
curl -X POST http://localhost:4000/link-analysis \
  -H "Content-Type: application/json" \
  -d '{"url": "https://stripe.com"}'
```

### Response (Excerpt from live execution)

```json
{
  "success": true,
  "website": "https://stripe.com",
  "brand": {
    "name": "Stripe",
    "category": "Financial Infrastructure / Payment Processing",
    "summary": "Stripe is a comprehensive financial services platform that enables businesses of all sizes to accept online and in-person payments, build flexible billing models, and manage global money movement."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Stripe is a leading financial infrastructure platform offering global payment processing, billing models, and financial tools for online and in-person commerce.",
      "business_category": "Financial Infrastructure / Payment Processing",
      "main_products_services": [
        "Online and In-Person Payments",
        "Subscription Billing",
        "Fraud Prevention",
        "Card Issuing",
        "Embedded Payments for Platforms"
      ],
      "competitors": [
        {
          "name": "PayPal",
          "main_service": "Digital wallet and online payment processing",
          "target_market": "Consumers and merchants of all sizes",
          "key_strength": "High brand recognition and consumer trust",
          "weakness_or_gap": "Less developer-centric customization compared to Stripe",
          "opportunity": "Target businesses seeking deeply embedded, highly customizable checkout experiences.",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Adyen",
          "main_service": "Global payment gateway and acquiring services",
          "target_market": "Large enterprise and global brands",
          "key_strength": "Unified single-platform architecture for online and in-person commerce",
          "weakness_or_gap": "Higher barrier to entry for smaller startups and SMBs",
          "opportunity": "Capture fast-growing startups before they scale into enterprise solutions.",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Square",
          "main_service": "POS hardware and integrated payment solutions",
          "target_market": "Small to medium brick-and-mortar businesses",
          "key_strength": "Seamless hardware and software integration for physical storefronts",
          "weakness_or_gap": "Historically less optimized for complex enterprise SaaS and global developer stacks",
          "opportunity": "Expand hybrid online-offline toolkits for modern SMBs.",
          "competitor_source": "AI-identified based on industry knowledge"
        }
      ],
      "brand_strengths": [
        "Extensible, reliable developer-first infrastructure with 99.999% uptime",
        "Comprehensive suite covering billing, tax, issuance, and fraud in one ecosystem",
        "Native support for 135+ currencies and multiple localized payment methods"
      ],
      "opportunities": [
        "Capitalize on emerging AI platform agentic payments and machine-to-machine transactions",
        "Deepen vertical POS integrations for specialized physical retail industries"
      ]
    },
    "target_search_queries": [
      {
        "query": "best payment gateway for global business",
        "platforms": ["Google"],
        "intent": "Service Search",
        "business_relevance": "Direct search intent for businesses seeking scalable international payments",
        "target_audience": "Technical founders and ecommerce operators"
      },
      {
        "query": "embedded financial infrastructure for platforms",
        "platforms": ["LinkedIn"],
        "intent": "B2B Search",
        "business_relevance": "Targets platform leaders and product managers evaluating monetized payments",
        "target_audience": "CTOs, Heads of Product, and Platform Architects"
      },
      {
        "query": "how to integrate online payments on website",
        "platforms": ["Facebook"],
        "intent": "Business Discovery",
        "business_relevance": "Educational entry point for SMB merchants setting up checkouts",
        "target_audience": "New business owners and entrepreneurs"
      },
      {
        "query": "subscription billing software for saas",
        "platforms": ["Instagram"],
        "intent": "Inspiration",
        "business_relevance": "Engages software founders seeking recurring billing architectures",
        "target_audience": "SaaS founders and growth marketers"
      },
      {
        "query": "fraud prevention tools for online payments",
        "platforms": ["X"],
        "intent": "Service Discovery",
        "business_relevance": "Engages fintech builders and security-conscious engineering teams",
        "target_audience": "Fintech developers and fraud risk managers"
      }
    ],
    "seo_improvements": {
      "primary_keyword": "financial infrastructure",
      "secondary_keywords": ["accept payments online", "payment gateway"],
      "long_tail_keywords": [
        "global payment infrastructure for enterprise saas",
        "automated usage based billing api",
        "integrated payment fraud prevention tools"
      ],
      "business_keywords": ["fintech api", "online money movement", "omnichannel payments"],
      "recommended_title": "Stripe | Financial Infrastructure to Grow Your Revenue",
      "title_primary_keyword": "financial infrastructure",
      "title_structure_notes": "Brand | Primary Keyword + Clear Value Proposition (<60 chars)",
      "meta_description": "Accept payments, build flexible billing models, and manage money movement globally with Stripe's complete financial infrastructure platform.",
      "business_summary": "Stripe builds economic infrastructure for the internet, enabling businesses from startups to global enterprises to accept payments, manage revenue operations, and launch new business models.",
      "meta_keywords": ["payments", "billing", "financial infrastructure", "fraud prevention", "issuing"],
      "supporting_content": [
        {
          "content_type": "blog post",
          "title": "Scaling SaaS Billing: Trends and Best Practices",
          "description": "Comprehensive guide detailing modern hybrid usage-based and subscription revenue models.",
          "target_keyword": "saas billing best practices"
        },
        {
          "content_type": "landing page",
          "title": "Stripe for Startups: Build and Scale Fast",
          "description": "Dedicated resource center detailing incorporation, payment activation, and initial credit discounts.",
          "target_keyword": "startup payment processing"
        },
        {
          "content_type": "FAQ",
          "title": "Global Payment Processing FAQ: Currencies, Methods, and Compliance",
          "description": "Answers to merchant queries on cross-border transactions, interchange fees, and regulatory requirements.",
          "target_keyword": "global payment gateway faq"
        }
      ]
    },
    "top_services": [
      {
        "service_name": "Online and In-Person Payment Processing",
        "description": "Higher authorization rates and unified commerce across online checkouts and physical terminals.",
        "target_industry": "E-commerce, Retail, and Digital Services",
        "target_customer": "Online retailers and multichannel merchants",
        "main_benefit": "Maximize checkout conversion with optimized localized payment rails.",
        "source": "website"
      },
      {
        "service_name": "Stripe Billing",
        "description": "Automated revenue collection, recurring invoicing, and usage-based subscriptions.",
        "target_industry": "Software and SaaS",
        "target_customer": "Subscription businesses and software companies",
        "main_benefit": "Eliminate billing friction and reduce involuntary churn with smart recovery.",
        "source": "website"
      },
      {
        "service_name": "Stripe Radar",
        "description": "Zero friction for genuine customers while blocking bad actors using adaptive machine learning.",
        "target_industry": "High-volume internet businesses",
        "target_customer": "Fraud risk teams and finance managers",
        "main_benefit": "Stop payment fraud without rejecting legitimate customer transactions.",
        "source": "website"
      },
      {
        "service_name": "Stripe Connect",
        "description": "New revenue streams and simplified multi-party payouts for platforms and marketplaces.",
        "target_industry": "Vertical SaaS and Marketplaces",
        "target_customer": "Platform executives and marketplace operators",
        "main_benefit": "Onboard sub-merchants and programmatically route payments at scale.",
        "source": "website"
      },
      {
        "service_name": "Professional Implementation Services",
        "description": "Faster time-to-market and minimized integration risk with guided architectural advisory.",
        "target_industry": "Enterprises and high-growth companies",
        "target_customer": "Enterprise CTOs and engineering directors",
        "main_benefit": "Accelerate mission-critical migrations with dedicated technical support.",
        "source": "website"
      }
    ],
    "target_audience": {
      "primary_audience": [
        {
          "audience_name": "Software Engineers & CTOs",
          "business_type": "Technology & SaaS",
          "requirement": "Reliable, well-documented APIs and scalable developer tools."
        },
        {
          "audience_name": "Startup Founders",
          "business_type": "Early-stage Companies",
          "requirement": "Fast incorporation, easy setup, and tools to accept payments quickly."
        }
      ],
      "secondary_audience": [
        {
          "audience_name": "Enterprise Finance Leaders",
          "business_type": "Large Retail & Enterprise",
          "requirement": "Omnichannel revenue consolidation and high uptime reliability."
        }
      ],
      "industries": [
        "SaaS and Software",
        "Retail and E-commerce",
        "Marketplaces",
        "Artificial Intelligence"
      ],
      "customer_needs": [
        "Global payment method support without localized entity overhead",
        "Automated compliance and PCI-DSS burden offloading",
        "Integrated subscription metrics and financial reconciliation"
      ],
      "geographical_focus": null,
      "customer_interests": [
        "API first architecture",
        "Global economic growth",
        "Frictionless checkout UX"
      ],
      "recommended_segments": [
        "Fast-scaling AI applications needing metered usage billing",
        "Platforms expanding into embedded banking services"
      ]
    }
  }
}
```

---

## Running Tests

The test suite covers unit validations, SSRF filters, schema boundary checks, rate limiting, and cache lifecycles.

```bash
# Run the entire test suite
pytest tests/ -v
```

### Test Suite Summary (26/26 Passing)

```text
tests/test_link_analysis.py::test_health_check PASSED                          [  3%]
tests/test_link_analysis.py::test_missing_url PASSED                           [  7%]
tests/test_link_analysis.py::test_invalid_url PASSED                           [ 11%]
tests/test_link_analysis.py::test_private_ip_blocked PASSED                    [ 15%]
tests/test_link_analysis.py::test_private_ip_10_blocked PASSED                 [ 19%]
tests/test_link_analysis.py::test_validate_url_good PASSED                     [ 23%]
tests/test_link_analysis.py::test_validate_url_ftp_rejected PASSED             [ 26%]
tests/test_link_analysis.py::test_validate_url_localhost_ssrf PASSED           [ 30%]
tests/test_link_analysis.py::test_validate_url_192_168_ssrf PASSED             [ 34%]
tests/test_link_analysis.py::test_validate_url_no_host PASSED                  [ 38%]
tests/test_link_analysis.py::test_validate_url_with_credentials_rejected PASSED [ 42%]
tests/test_link_analysis.py::test_validate_url_non_standard_port_rejected PASSED [ 46%]
tests/test_link_analysis.py::test_full_analysis_mocked PASSED                  [ 50%]
tests/test_link_analysis.py::test_llm_runtime_error_returns_502 PASSED         [ 53%]
tests/test_link_analysis.py::test_too_few_competitors_returns_502 PASSED       [ 57%]
tests/test_link_analysis.py::test_too_many_competitors_returns_502 PASSED      [ 61%]
tests/test_link_analysis.py::test_wrong_query_count_returns_502 PASSED         [ 65%]
tests/test_link_analysis.py::test_wrong_service_count_returns_502 PASSED       [ 69%]
tests/test_link_analysis.py::test_insufficient_supporting_content_returns_502 PASSED [ 73%]
tests/test_link_analysis.py::test_cache_hit_skips_extractor_and_llm PASSED   [ 76%]
tests/test_link_analysis.py::test_website_inaccessible_returns_400 PASSED      [ 80%]
tests/test_link_analysis.py::test_rate_limit_returns_429 PASSED                [ 84%]
tests/test_link_analysis.py::test_cache_set_and_get PASSED                     [ 88%]
tests/test_link_analysis.py::test_cache_expired_entry_returns_none PASSED      [ 92%]
tests/test_link_analysis.py::test_cache_normalises_trailing_slash PASSED       [ 96%]
tests/test_link_analysis.py::test_cache_invalidate PASSED                      [100%]
============================== 26 passed in 1.88s ==============================
```

---

## LLM Platform Comparison & Recommendation

### A. Provider Platform Comparison

Comparison across leading fast-tier inference models using current published rates:

| Criteria | Google Gemini 3.5 Flash-Lite *(Integrated)* | OpenAI GPT-6 Luna | Anthropic Claude Haiku 5.5 |
|---|---|---|---|
| **Provider** | Google | OpenAI | Anthropic |
| **Model Name** | `gemini-3.5-flash-lite` | `gpt-6-luna` | `claude-haiku-5-5` |
| **Input Cost (per 1M tokens)** | $0.30 | **$0.10** | **$0.10** (base ≤100k) |
| **Output Cost (per 1M tokens)** | $2.50 | **$0.50** | **$0.50** (base ≤100k) |
| **Context Window** | **1,048,576 tokens** | 1,050,000 tokens | 1,000,000 tokens |
| **Native JSON Schema Mode** | `responseMimeType: application/json` | Structured Outputs | Structured Outputs |
| **Local Benchmark Evidence** | **Measured** (76.89s cold w/ retries; 13,995 total tokens; $0.0093/call) | *Unmeasured in this project* | *Unmeasured in this project* |
| **Official Documentation** | [Google Pricing](https://ai.google.dev/gemini-api/docs/pricing) | [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-6-luna) | [Anthropic Docs](https://platform.claude.com/docs/en/models/haiku-5-5/overview) |

> **Pricing note:** Claude Haiku 5.5 lists a base pricing of $0.10 input / $0.50 output per million tokens for prompts under 100,000 tokens, which rises to $0.50 input / $2.50 output for prompt contexts exceeding 100k tokens.

### B. Selection Rationale

**Selected: Google Gemini 3.5 Flash-Lite**

1. **Assignment Alignment**: Already integrated in the codebase with verified end-to-end execution and schema compliance.
2. **Context Capacity**: 1,048,576 tokens context window easily handles large landing pages and eliminates token boundary issues.
3. **Structured Outputs**: Fully supports strict JSON generation, verified against Pydantic schema validation across 26 tests and live runs.
4. **Cost Assessment**: At **$0.0093 per full 5-section enterprise analysis** (11,669 input + 2,326 output tokens), it delivers production-grade business insights at sub-cent cost per request. While GPT-6 Luna lists lower nominal per-token pricing, Gemini 3.5 Flash-Lite is operational, tested, and satisfies all requirements.

---

## Cost Optimization Strategies

| Strategy | Implementation | Evidence & Measured Impact |
|---|---|---|
| **HTML Cleaning** | Strips `<script>`, `<style>`, comments, `<svg>`, `<iframe>` before extracting text | **93.7% reduction measured**: On `stripe.com`, raw HTML was 724,310 bytes (723,039 chars), compressed down to 45,489 characters of meaningful content. |
| **Hard Truncation Cap** | Caps body extraction at 50,000 characters (~12,500 tokens) | **Prevents runaway token bills** on documentation sites or large single-page applications. |
| **Single-Prompt Consolidation** | Gathers all 5 analysis sections in one LLM call | **80% fewer round-trips**: Avoids repeating system prompts, extraction context, and TLS handshakes across 5 separate calls. |
| **In-Memory TTL Caching** | Serves cached analyses for normalized URLs (`3600s` TTL) | **100% cost reduction on repeats**: Repeat visits within the TTL window resolve in **1.746 ms** with 0 external HTTP/LLM calls. |
| **Sliding-Window Rate Limiting** | Restricts bursts per IP address via pure ASGI middleware | **Quota protection**: Prevents client loops or denial-of-service from exhausting upstream provider tokens. |

---

## Competitor Intelligence & Sourcing

### Current Implementation (AI-Derived Suggestions)
In this implementation, competitors are generated by Gemini using its trained industry knowledge. To ensure complete transparency:
- Every competitor object includes the explicit field:
  ```json
  "competitor_source": "AI-identified based on industry knowledge"
  ```
- Competitors are returned as structured competitive suggestions, not empirical scraped analytics.

### Extensibility: `CompetitorService` Architecture Hook
The codebase includes [`CompetitorService`](app/services/competitor_service.py) wired directly into [`AnalysisService`](app/services/analysis_service.py).
When external competitive intelligence API keys (e.g., SimilarWeb, SEMrush, Ahrefs, Crunchbase) are configured, `CompetitorService.enrich_competitors()` provides the hook to:
1. Validate competitor domain presence and traffic share.
2. Augment qualitative strengths with organic keyword overlap telemetry.
3. Verify company URLs and employee counts without modifying core pipeline orchestration.

---

## Error Handling

| Scenario | HTTP Status | Response Message / Behavior |
|---|---|---|
| **Missing or Malformed URL** | `422` | FastAPI Pydantic schema validation error |
| **Private or Local IP Target (SSRF)** | `400` | `"URL blocked for security reasons: ..."` |
| **Non-Standard Port / URL Credentials** | `400` | `"Invalid URL: ..."` |
| **Website Inaccessible or DNS Failure** | `400` | `"Could not access the website: ..."` |
| **Decompressed Response Exceeds 5 MB** | `400` | `"Website response exceeds the configured size limit"` |
| **Redirect Loop (>10 hops)** | `400` | `"Redirect loop detected"` |
| **Rate Limit Exceeded** | `429` | `{"detail": "Rate limit exceeded. Please slow down and try again later."}` with `Retry-After` header |
| **Missing API Key** | `500` | `"GEMINI_API_KEY is not set. Please add it to your .env file."` |
| **LLM Service Failure (e.g. Quota/503)** | `502` | `"The analysis provider could not complete the request."` |
| **Incomplete LLM Output (Item counts invalid)** | `502` | Count mismatch detail (e.g. `"The analysis provider returned 2 competitors; exactly 3 are required."`) |

---

## Security

- **Multi-Layer SSRF Defense**:
  - Restricts schemes strictly to `http` and `https`.
  - Disallows credentials (`user:pass@host`) and non-standard HTTP ports (blocks everything except 80/443).
  - Explicitly blocks local names (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`).
  - Pre-resolves DNS and checks each IP against IPv4 and IPv6 private, reserved, loopback, and carrier-grade NAT blocks.
  - **DNS Pinning**: Enforces pinned socket connections via `_PinnedResolver` to eliminate DNS rebinding (TOCTOU) exploits.
  - **Manual Redirect Auditing**: Disables automatic HTTP redirects (`allow_redirects=False`); re-validates each redirect hop destination before following.
- **Buffer & Memory Protection**:
  - Streams HTTP content with chunked reading capped at `MAX_RESPONSE_BYTES` (5 MB) to prevent zip-bomb / decompressed payload denial-of-service.
- **Non-Root Container Execution**:
  - Docker container creates and executes under dedicated unprivileged system user `app`.
- **Secret Isolation**:
  - Sensitive API keys are loaded via `.env` and strictly excluded from git tracking and Docker build contexts.

---

## Submission & Verification Checklist

To complete the public assignment submission:

- [x] **Local Git Repository**: Committed with clean working tree.
- [x] **26/26 Unit & Integration Tests Passing**: Verified with pytest.
- [x] **Live Run Evidence**: `live_run.log` and `live_run_output.json` tracked and checked into the repository.
- [ ] **Public GitHub Repository**:
  1. Create a new public repository on GitHub (e.g. `dxora_link_analysis`).
  2. Push the local commits:
     ```bash
     git remote add origin https://github.com/<your-username>/dxora_link_analysis.git
     git branch -M main
     git push -u origin main
     ```
- [ ] **Public Deployment (Optional / Live Demo)**:
  - If deploying to Render, Railway, or Fly.io:
    - Set environment variable `GEMINI_API_KEY` in the hosting dashboard.
    - Provide the live URL (e.g., `https://your-app.onrender.com/docs`).
- [ ] **Social Account Verification / Submission Email**: Send the public GitHub repository link and deployed demo link according to the assignment instructions.

---

## License

MIT © 2026 Dxora Link Analysis contributors
