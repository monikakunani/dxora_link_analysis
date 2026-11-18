# AI-Powered Website Link Analysis API

> A production-grade FastAPI microservice that extracts website content, conducts deep brand and competitive analysis via Google Gemini LLM, and produces structured SEO, service, and audience intelligence.

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
- [Live Benchmark & Real Run Verification](#live-benchmark--real-run-verification)
- [Sample API Request & Response](#sample-api-request--response)
- [Running Tests](#running-tests)
- [LLM Platform Comparison & Recommendation](#llm-platform-comparison--recommendation)
- [Cost Optimization Strategies](#cost-optimization-strategies)
- [Error Handling](#error-handling)
- [Security](#security)

---

## Features

- **SSRF-Safe Content Extraction**: Fetches and parses website HTML using `aiohttp` + `BeautifulSoup4` with DNS pinning, manual redirect verification, and a 5 MB streaming cap.
- **LLM-Powered Business Intelligence**: Uses Google Gemini (`gemini-3.5-flash-lite`) to analyze page context in a single cost-optimized prompt.
- **5-Section Structured Analysis**:
  1. **Competitor vs Your Brand Analysis**: Pinpoints brand strengths, opportunities, and exactly 3 key market competitors with verified sourcing labels.
  2. **Top 5 Target Search Queries**: Generates exactly 5 queries tailored to 5 major platforms (Google, Facebook, Instagram, LinkedIn, X).
  3. **SEO Improvement Recommendations**: Primary, secondary, long-tail keywords, title tag, meta description, and 3+ supporting content recommendations.
  4. **Top 5 Services Identification**: Exactly 5 key services labeled as explicitly mentioned (`website`) or recommended (`inferred`).
  5. **Target Audience Identification**: Primary & secondary audience segments, user needs, and relevant industries.
- **In-Memory TTL Caching**: Eliminates duplicate LLM calls on repeated URLs using normalized URL keys.
- **Pure-ASGI Sliding-Window Rate Limiting**: Protects upstream LLM quotas per client IP (default: 60 req/min).
- **Strict Pydantic Validation**: Guaranteed response structure and exact item count constraints.

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
7. `LLMService` submits content to Gemini with exponential backoff retries for transient errors.
8. `AnalysisService` verifies counts, triggers competitor enrichment hook, caches the result, and returns the response.

---

## Project Structure

```text
dxora_link_analysis/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application, routes, and ASGI rate limiter
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
├── live_run_output.json           # Raw JSON response from live Gemini run against stripe.com
├── live_run.log                   # Full console execution log of real Gemini run
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
| `REQUEST_TIMEOUT` | `30` | Website fetch timeout (seconds) |
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

The container runs as an unprivileged non-root user (`app`), incorporates an automated Docker health check against `GET /`, and omits environment files via `.dockerignore`.

---

## API Documentation

Interactive OpenAPI documentation is automatically served:

- **Swagger UI**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc**: [http://localhost:4000/redoc](http://localhost:4000/redoc)

---

## Live Benchmark & Real Run Verification

A real live analysis was executed against `https://stripe.com` using the live Google Gemini API (`gemini-3.5-flash-lite`).

The full verifiable artifacts are checked in:
- Full output JSON: [`live_run_output.json`](live_run_output.json)
- Formatted execution log: [`live_run.log`](live_run.log)

### Measured Performance Benchmark

| Pipeline Stage | Measured Latency | Tokens / Volume | Notes |
|---|---|---|---|
| **Website Fetch & Extraction** | 1.6s – 5.6s | 45,489 chars | aiohttp + BS4 cleaning noise & de-duplicating paragraphs |
| **Gemini 3.5 Flash-Lite Analysis** | 15.0s – 15.8s | ~11.5k input / ~2.1k output | Full 5-section structured JSON generation in 1 prompt |
| **Schema Validation & Enrichment** | 0.01s | In-memory | Strict Pydantic parsing & constraint verification |
| **Total End-to-End Latency** | **16.6s – 21.4s** | — | **0.00s on repeated runs** (served directly from cache) |

### Real Run Quality Audit

- **Brand Extraction**: Correctly identified brand as `Stripe` and category as `Financial Services & Payment Infrastructure`.
- **Competitor Identification**: Correctly proposed **PayPal**, **Adyen**, and **Square** with relevant key strengths, gaps, and differentiation opportunities. Labeled explicitly with `competitor_source: "AI-identified based on industry knowledge"`.
- **Top Services**: Extracted 5 core services (*Online and In-Person Payments*, *Flexible Billing*, *Fraud Prevention (Radar)*, *Card Issuing*, *Embedded Financial Services*) directly from website text (`source: "website"`).
- **Search Queries**: Delivered 5 targeted queries mapped to distinct platforms (*Google: Service Search*, *Facebook: Business Discovery*, *LinkedIn: B2B Search*, *X: Service Discovery*, *Instagram: Inspiration*).
- **SEO & Audience**: Produced targeted title, meta description, 3 distinct content formats (blog post, landing page, FAQ), and segmented primary (software engineers, CTOs) from secondary audiences (startup founders, enterprise leaders).

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
    "category": "Financial Services & Payment Infrastructure",
    "summary": "Stripe is a financial infrastructure platform that helps businesses of all sizes accept online and in-person payments, manage billing models, and handle global money movement."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Stripe is a leading financial infrastructure platform offering global payment processing, billing models, and financial tools for online and in-person commerce.",
      "business_category": "Financial Services & Payment Infrastructure",
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
          "opportunity": "Target developers seeking advanced API integrations and flexible custom revenue models",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Adyen",
          "main_service": "Global payment gateway and acquiring services",
          "target_market": "Large enterprise and global brands",
          "key_strength": "Unified single-platform architecture for global enterprise scale",
          "weakness_or_gap": "Higher barrier to entry for smaller startups and SMBs",
          "opportunity": "Highlight user-friendly startup onboarding and no-code tools to capture fast-growing companies",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Square",
          "main_service": "POS hardware and integrated payment solutions",
          "target_market": "Small to medium brick-and-mortar businesses",
          "key_strength": "Strong ecosystem of physical point-of-sale hardware and software",
          "weakness_or_gap": "Historically less optimized for complex enterprise SaaS and global developer stacks",
          "opportunity": "Promote advanced software extensibility and developer APIs for tech-forward businesses",
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
        "query": "financial infrastructure for online payments",
        "platforms": ["Google"],
        "intent": "Service Search",
        "business_relevance": "Direct intent for businesses seeking developer-grade payment backbones",
        "target_audience": "Technical founders and engineering leads"
      },
      {
        "query": "modern billing software for recurring revenue",
        "platforms": ["LinkedIn"],
        "intent": "B2B Search",
        "business_relevance": "Captures finance decision-makers modernizing subscription models",
        "target_audience": "CFOs, Finance Directors, and SaaS Operations"
      },
      {
        "query": "how to add global checkout to ecommerce store",
        "platforms": ["Facebook"],
        "intent": "Business Discovery",
        "business_relevance": "Educates SMB owners scaling into international markets",
        "target_audience": "E-commerce store operators and merchants"
      },
      {
        "query": "best checkout flow examples for mobile conversion",
        "platforms": ["Instagram"],
        "intent": "Inspiration",
        "business_relevance": "Attracts designers and product managers evaluating UX quality",
        "target_audience": "UI/UX Designers and Growth Marketers"
      },
      {
        "query": "stablecoin and crypto payout integration for developers",
        "platforms": ["X"],
        "intent": "Service Discovery",
        "business_relevance": "Engages web3 and fintech developers exploring modern payout rails",
        "target_audience": "Fintech developers and crypto builders"
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
      "meta_description": "Stripe is a financial services platform that helps all types of businesses accept payments, build flexible billing models and manage money movement.",
      "business_summary": "Stripe builds economic infrastructure for the internet, enabling businesses from startups to global enterprises to accept payments, manage revenue operations, and launch new business models.",
      "meta_keywords": ["payments", "billing", "financial infrastructure", "fraud prevention", "issuing"],
      "supporting_content": [
        {
          "content_type": "blog post",
          "title": "Scaling SaaS Billing in 2026: Trends and Best Practices",
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
        "service_name": "Online and In-Person Payments",
        "description": "Accept and optimize payments globally across digital channels and physical point-of-sale terminals.",
        "target_industry": "E-commerce, Retail, and Digital Services",
        "target_customer": "Online retailers and multichannel merchants",
        "main_benefit": "Maximize authorization rates and conversion with a unified checkout architecture.",
        "source": "website"
      },
      {
        "service_name": "Flexible Billing",
        "description": "Implement custom revenue models, subscriptions, and usage-based billing structures easily.",
        "target_industry": "Software and SaaS",
        "target_customer": "Subscription businesses and software companies",
        "main_benefit": "Eliminate billing friction and reduce involuntary churn with automated recovery tools.",
        "source": "website"
      },
      {
        "service_name": "Fraud Prevention (Radar)",
        "description": "Stop fraudulent transactions and card testing without blocking legitimate customer growth.",
        "target_industry": "High-volume internet businesses",
        "target_customer": "Fraud risk teams and finance managers",
        "main_benefit": "Adaptive machine learning protects revenue without adding unnecessary buyer friction.",
        "source": "website"
      },
      {
        "service_name": "Card Issuing",
        "description": "Create, manage, and scale your own card issuing program with embedded financial tools.",
        "target_industry": "Fintech and On-Demand Marketplaces",
        "target_customer": "Platform operators and commercial fleet managers",
        "main_benefit": "Programmatically issue physical or virtual cards with custom spend limits in minutes.",
        "source": "website"
      },
      {
        "service_name": "Embedded Financial Services for Platforms",
        "description": "Integrate payments and financial services directly into your vertical SaaS platform.",
        "target_industry": "Vertical SaaS and Marketplaces",
        "target_customer": "Platform executives and product managers",
        "main_benefit": "Monetize software platforms and deliver seamless payment experiences to sub-merchants.",
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
          "requirement": "Fast incorporation, easy setup, and tools to fundraise and accept payments quickly."
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

### A. Comparative Evaluation Across Providers

| Criteria | Google Gemini 3.5 Flash-Lite *(Selected)* | OpenAI GPT-4o-mini | Anthropic Claude 3.5 Haiku |
|---|---|---|---|
| **Input Cost (per 1M tokens)** | **$0.30** | $0.15 | $0.80 |
| **Output Cost (per 1M tokens)** | **$2.50** | $0.60 | $4.00 |
| **Measured Response Speed** | **15.0s – 15.8s** *(Measured live)* | ~12s – 18s *(Estimated)* | ~10s – 16s *(Estimated)* |
| **Output Reliability** | **100% Schema Compliance** *(Verified)* | High (Structured Outputs) | High (JSON Mode) |
| **Context Window** | **1,048,576 tokens** | 128,000 tokens | 200,000 tokens |
| **Native JSON Schema Mode** | `responseMimeType: application/json` | `response_format: json_schema` | Tool calling / Pre-fill |
| **Cost per 10k Input / 2k Output Analysis** | **$0.0080** | $0.0027 | $0.0160 |

### B. Why Gemini 3.5 Flash-Lite?

1. **Context Window Headroom**: The 1M+ context window easily accommodates full landing pages with zero risk of context overflow even before content cleaning.
2. **Deterministic JSON Formatting**: Combined with Pydantic validation, Gemini's JSON mode guarantees exact section and field key compliance.
3. **Cost Efficiency**: At less than $0.01 per full 5-section enterprise analysis, it offers an optimal balance of operational affordability and output richness.
4. **Resilience**: Integrated automatic exponential backoff gracefully handles transient 429/503 spikes.

---

## Cost Optimization Strategies

| Strategy | Technical Mechanism | Savings Rationale & Calculation Basis |
|---|---|---|
| **HTML Cleaning** | Strips `<script>`, `<style>`, comments, `<svg>`, `<iframe>` before parsing | **40%–60% token reduction**: CSS styles and JS bundle blobs constitute 50%+ of raw modern web page size. |
| **Content Deduplication** | Discards repeating footer links, duplicate nav text, and boilerplate strings | **10%–20% token reduction**: Removes repetitive site navigation headers and footer disclaimer text. |
| **Hard Truncation Cap** | Caps body extraction at 50,000 characters (~12,500 tokens) | **Cost spike prevention**: Protects against runaway token bills on massive docs sites or single-page apps. |
| **Single-Prompt Consolidation** | Gathers all 5 analysis dimensions in 1 LLM inference pass | **80% call reduction**: 1 API request vs. 5 separate round-trips avoids repeated system prompt and context re-ingestion. |
| **In-Memory TTL Caching** | Serves cached analyses for normalized URLs (`3600s` TTL) | **100% cost reduction on repeats**: Repeat visits within the TTL window make 0 external HTTP/LLM calls. |
| **Sliding-Window Rate Limiting** | Restricts bursts per IP address via pure ASGI middleware | **Quota protection**: Prevents malicious or misconfigured clients from exhausting provider quotas. |

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
| **Incomplete LLM Output (Item counts invalid)** | `502` | Explicit count mismatch detail (e.g. `"The analysis provider returned 2 competitors; exactly 3 are required."`) |

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

## License

MIT © 2026 Dxora Link Analysis contributors
