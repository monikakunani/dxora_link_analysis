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
│   ├── static/
│   │   ├── index.html             # Web UI: analyze a URL, browse the 5 sections in tabs
│   │   └── health.html            # Human-readable service status page
│   └── utils/
│       ├── __init__.py
│       └── validators.py          # Multi-layer SSRF prevention & URL sanitization
├── tests/
│   ├── __init__.py
│   └── test_link_analysis.py      # Full test suite (32/32 tests passing)
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

- **Python 3.10 – 3.13** (tested on Python 3.13; the pinned `pydantic-core` has no wheel for 3.15 yet)
- **Google Gemini API Key** – Obtainable from [Google AI Studio](https://aistudio.google.com/apikey)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/monikakunani/dxora_link_analysis.git
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

| URL | What it is |
|---|---|
| [`/`](http://localhost:4000/) | **Web UI**: paste a website URL and browse the five sections as tables and cards (tabs for Competitors, Search queries, SEO, Top services, Audience, and Raw JSON with copy/download) |
| [`/link-analysis`](http://localhost:4000/docs#/Analysis) | The REST endpoint (`POST`, JSON in/out) |
| [`/docs`](http://localhost:4000/docs) | Swagger UI for trying the API directly |
| [`/health`](http://localhost:4000/health) | Service status. Browsers get a status page (server online, AI key configured, model, uptime, cache size, response time; auto-refreshes). Monitoring tools, `curl` and the Docker `HEALTHCHECK` get JSON. The API key itself is never exposed. |

The web UI is a single dependency-free HTML file ([`app/static/index.html`](app/static/index.html)) that calls the same `POST /link-analysis` endpoint. All text from the analyzed site and the LLM is HTML-escaped before rendering.

### Deploy to Render (free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/monikakunani/dxora_link_analysis)

The included [`render.yaml`](render.yaml) builds the Dockerfile, uses `/health` as the health check, and prompts for `GEMINI_API_KEY` at deploy time, so the key is never stored in the repository.

### Docker Deployment

Build and run the self-contained container:

```bash
docker build -t dxora-link-analysis .
docker run --rm -p 4000:4000 --env-file .env dxora-link-analysis
```

The container listens on `$PORT` (default `4000`), so it runs unchanged on Render, Railway, Fly.io or Cloud Run, which inject their own port. Verified locally: built the image, ran it with `PORT=8080`, completed a live analysis, confirmed the SSRF block, and Docker's `HEALTHCHECK` reported `healthy`.

The container runs as an unprivileged non-root user (`app`), incorporates an automated Docker health check against `GET /health`, and excludes local environment secrets via `.dockerignore`.

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
| **Raw HTML Downloaded** | **729,197 bytes** (727,926 chars) | Live stream from `https://stripe.com` |
| **Cleaned Text Extracted** | **7,589 chars** | Script/style/SVG removal + leaf-block extraction (no nested-wrapper duplication) |
| **Content Reduction** | **99.0% reduction** | `(1 - 7,589 / 727,926) * 100` |
| **Gemini Prompt Tokens** | **3,906 tokens** | Reported by Gemini `usageMetadata.promptTokenCount` |
| **Gemini Output Tokens** | **2,482 tokens** | Reported by Gemini `usageMetadata.candidatesTokenCount` |
| **Gemini Total Tokens** | **6,388 tokens** | Reported by Gemini `usageMetadata.totalTokenCount` |
| **Calculated Inference Cost** | **$0.007377 USD** | Standard Gemini rates: `(3,906 * $0.30 + 2,482 * $2.50) / 1,000,000` |
| **Cold Run Latency** | **8.60s** | 729 KB download + extraction + one Gemini call (no retries needed on this run) |
| **Warm Cache Hit Latency** | **0.217 ms (0.0002s)** | Measured on repeat request to `AnalysisService.analyze()` |
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
    "category": "Financial Services & Payment Infrastructure",
    "summary": "Stripe is a financial services platform that provides payment processing, custom billing models, and financial infrastructure for businesses of all sizes, from startups to global enterprises."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Stripe provides comprehensive financial infrastructure, payment processing, fraud prevention, and billing tools designed for online and in-person commerce.",
      "business_category": "Financial Services & Payment Processing",
      "main_products_services": [
        "Online and in-person payment processing",
        "Flexible billing and subscription management",
        "Fraud prevention and risk management",
        "Card issuing programs",
        "Embedded financial services for platforms"
      ],
      "your_brand": {
        "name": "Stripe",
        "main_service": "Global payment processing and financial infrastructure",
        "target_market": "Businesses of all sizes, from startups to Fortune 100 enterprises",
        "key_strength": "Robust developer-friendly APIs, high reliability, and extensive global reach",
        "opportunity": "Expanding deeper into AI-powered agentic commerce and crypto/stablecoin payments"
      },
      "competitors": [
        {
          "name": "PayPal",
          "main_service": "Online payment processing and digital wallet services",
          "target_market": "Consumers and merchants of all sizes globally",
          "key_strength": "High brand recognition and massive consumer wallet base",
          "weakness_or_gap": "Less developer-centric and customizable than modern API-first alternatives",
          "opportunity": "Capture enterprise developers looking for advanced customization and no-code tools",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Adyen",
          "main_service": "Global payment platform for enterprise businesses",
          "target_market": "Large enterprise retailers and global brands",
          "key_strength": "Unified single-platform architecture for online and in-store payments worldwide",
          "weakness_or_gap": "Less optimized for early-stage startups and small businesses",
          "opportunity": "Target high-growth startups before they reach enterprise scale",
          "competitor_source": "AI-identified based on industry knowledge"
        },
        {
          "name": "Square",
          "main_service": "Point-of-sale hardware and software for small businesses",
          "target_market": "Small and medium-sized local businesses, retail, and food service",
          "key_strength": "Strong ecosystem of physical hardware and integrated POS solutions",
          "weakness_or_gap": "Less suitable for complex, high-volume software platforms and global online SaaS billing",
          "opportunity": "Provide hybrid online-offline solutions for growing retail brands",
          "competitor_source": "AI-identified based on industry knowledge"
        }
      ],
      "brand_strengths": [
        "Developer-first ecosystem with rich APIs and documentation",
        "Massive global scale processing trillions in volume with high uptime"
      ],
      "opportunities": [
        "Capitalize on emerging stablecoin and crypto payment methods",
        "Integrate commerce capabilities directly into AI platforms"
      ]
    },
    "target_search_queries": [
      {
        "query": "how to accept online payments for ecommerce",
        "platforms": [
          "Google"
        ],
        "intent": "Service Search",
        "business_relevance": "Directly targets merchants looking for payment gateway solutions.",
        "target_audience": "Small business owners and ecommerce founders"
      },
      {
        "query": "best payment gateway for growing SaaS businesses",
        "platforms": [
          "Facebook"
        ],
        "intent": "Business Discovery",
        "business_relevance": "Captures business owners seeking subscription billing infrastructure.",
        "target_audience": "Startup founders and SaaS operators"
      },
      {
        "query": "how to implement usage-based billing models",
        "platforms": [
          "Instagram"
        ],
        "intent": "Inspiration",
        "business_relevance": "Highlights modern billing features offered by the platform.",
        "target_audience": "Product managers and developers"
      },
      {
        "query": "embedded financial services for software platforms",
        "platforms": [
          "LinkedIn"
        ],
        "intent": "B2B Search",
        "business_relevance": "Targets platform leaders looking to monetize transactions.",
        "target_audience": "Platform executives and fintech product leads"
      },
      {
        "query": "accept crypto and stablecoin payments at checkout",
        "platforms": [
          "X"
        ],
        "intent": "Service Discovery",
        "business_relevance": "Aligns with cutting-edge crypto payment integrations.",
        "target_audience": "Tech-forward merchants and crypto enthusiasts"
      }
    ],
    "seo_improvements": {
      "primary_keyword": "financial infrastructure",
      "secondary_keywords": [
        "payment processing",
        "online payments"
      ],
      "long_tail_keywords": [
        "accept payments globally online",
        "custom revenue models for SaaS"
      ],
      "business_keywords": [
        "billing models",
        "fraud prevention"
      ],
      "recommended_title": "Stripe | Financial Infrastructure to Grow Your Revenue",
      "title_primary_keyword": "financial infrastructure",
      "title_structure_notes": "Brand name followed by value proposition containing primary keyword.",
      "meta_description": "Stripe is a financial services platform that helps all types of businesses accept payments, build flexible billing models and manage money movement.",
      "business_summary": "Financial platform for global commerce, payments, and revenue management.",
      "meta_keywords": [
        "payments",
        "financial services"
      ],
      "supporting_content": [
        {
          "content_type": "landing page",
          "title": "Stripe for Startups: Scale Your Business Fast",
          "description": "Discover tools and resources designed to help early-stage startups incorporate, fundraise, and accept payments.",
          "target_keyword": "startup payment infrastructure"
        },
        {
          "content_type": "blog post",
          "title": "The Future of Agentic Commerce and AI Payments",
          "description": "Learn how businesses can make their products shoppable through AI platforms using new protocols.",
          "target_keyword": "AI payments commerce"
        },
        {
          "content_type": "FAQ",
          "title": "Stripe Billing and Subscription Management FAQ",
          "description": "Answers to common questions about setting up flexible billing models, invoicing, and usage-based pricing.",
          "target_keyword": "subscription billing models"
        }
      ]
    },
    "top_services": [
      {
        "service_name": "Online and In-Person Payment Processing",
        "description": "Accept payments globally across online checkouts, in-person terminals, and digital wallets.",
        "target_industry": "Retail & Ecommerce",
        "target_customer": "Businesses of all sizes",
        "main_benefit": "Optimized conversion rates and global payment method support.",
        "source": "website"
      },
      {
        "service_name": "Flexible Billing and Subscriptions",
        "description": "Enable any billing model including recurring subscriptions and usage-based pricing.",
        "target_industry": "SaaS & Software",
        "target_customer": "Subscription-based businesses",
        "main_benefit": "Automated revenue collection and reduced churn.",
        "source": "website"
      },
      {
        "service_name": "Fraud and Risk Management",
        "description": "Stop fraud, card testing, and bot abuse without halting legitimate growth.",
        "target_industry": "Financial Services & Commerce",
        "target_customer": "Online merchants",
        "main_benefit": "Advanced machine learning risk profiling.",
        "source": "website"
      },
      {
        "service_name": "Embedded Financial Services for Platforms",
        "description": "Embed payments and financial services directly into vertical SaaS platforms.",
        "target_industry": "Vertical SaaS",
        "target_customer": "Software platform operators",
        "main_benefit": "New revenue streams through monetized platform transactions.",
        "source": "website"
      },
      {
        "service_name": "Custom Card Issuing",
        "description": "Create, manage, and distribute physical and virtual corporate payment cards.",
        "target_industry": "Fintech & Enterprise",
        "target_customer": "Growing enterprises and fintechs",
        "main_benefit": "Full control over card spending limits and branding.",
        "source": "website"
      }
    ],
    "target_audience": {
      "primary_audience": [
        {
          "audience_name": "Startup Founders",
          "business_type": "Early-stage startup",
          "requirement": "Fast setup, incorporation, and foundational payment acceptance."
        },
        {
          "audience_name": "Enterprise Product Managers",
          "business_type": "Fortune 500 / Enterprise",
          "requirement": "Reliable global commerce orchestration and custom workflows."
        }
      ],
      "secondary_audience": [
        {
          "audience_name": "Platform Operators",
          "business_type": "Vertical SaaS",
          "requirement": "Embedded payments and multi-party money movement."
        },
        {
          "audience_name": "Developers",
          "business_type": "Technology",
          "requirement": "Robust APIs, SDKs, and clean technical documentation."
        }
      ],
      "industries": [
        "Ecommerce",
        "SaaS",
        "Retail",
        "Artificial Intelligence",
        "Financial Services"
      ],
      "business_types": [
        "Startups",
        "SMBs",
        "Vertical SaaS Platforms",
        "Fortune 100 Enterprises"
      ],
      "customer_profiles": [
        "Tech-savvy startup founders building global software and SaaS products",
        "Enterprise directors of finance looking to unify online and in-store commerce"
      ],
      "customer_needs": [
        "Secure payment processing",
        "Global currency support",
        "Automated recurring billing",
        "Low operational overhead"
      ],
      "geographical_focus": null,
      "customer_interests": [
        "Financial technology",
        "Business growth",
        "AI integration",
        "International expansion"
      ],
      "recommended_segments": [
        "High-growth AI startups",
        "Global enterprise retailers",
        "B2B SaaS platforms"
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

### Test Suite Summary (32/32 Passing)

```text
tests/test_link_analysis.py::test_health_check PASSED [  3%]
tests/test_link_analysis.py::test_health_reports_config_without_leaking_key PASSED [  6%]
tests/test_link_analysis.py::test_health_in_browser_returns_status_page PASSED [  9%]
tests/test_link_analysis.py::test_docs_page_links_back_to_ui PASSED [ 12%]
tests/test_link_analysis.py::test_web_ui_served_at_root PASSED [ 15%]
tests/test_link_analysis.py::test_missing_url PASSED [ 18%]
tests/test_link_analysis.py::test_invalid_url PASSED [ 21%]
tests/test_link_analysis.py::test_private_ip_blocked PASSED [ 25%]
tests/test_link_analysis.py::test_private_ip_10_blocked PASSED [ 28%]
tests/test_link_analysis.py::test_validate_url_good PASSED [ 31%]
tests/test_link_analysis.py::test_validate_url_ftp_rejected PASSED [ 34%]
tests/test_link_analysis.py::test_validate_url_localhost_ssrf PASSED [ 37%]
tests/test_link_analysis.py::test_validate_url_192_168_ssrf PASSED [ 40%]
tests/test_link_analysis.py::test_validate_url_no_host PASSED [ 43%]
tests/test_link_analysis.py::test_validate_url_with_credentials_rejected PASSED [ 46%]
tests/test_link_analysis.py::test_validate_url_non_standard_port_rejected PASSED [ 50%]
tests/test_link_analysis.py::test_full_analysis_mocked PASSED [ 53%]
tests/test_link_analysis.py::test_llm_runtime_error_returns_502 PASSED [ 56%]
tests/test_link_analysis.py::test_too_few_competitors_returns_502 PASSED [ 59%]
tests/test_link_analysis.py::test_too_many_competitors_returns_502 PASSED [ 62%]
tests/test_link_analysis.py::test_wrong_query_count_returns_502 PASSED [ 65%]
tests/test_link_analysis.py::test_wrong_service_count_returns_502 PASSED [ 68%]
tests/test_link_analysis.py::test_insufficient_supporting_content_returns_502 PASSED [ 71%]
tests/test_link_analysis.py::test_cache_hit_skips_extractor_and_llm PASSED [ 75%]
tests/test_link_analysis.py::test_website_inaccessible_returns_400 PASSED [ 78%]
tests/test_link_analysis.py::test_rate_limit_returns_429 PASSED [ 81%]
tests/test_link_analysis.py::test_cache_set_and_get PASSED [ 84%]
tests/test_link_analysis.py::test_cache_expired_entry_returns_none PASSED [ 87%]
tests/test_link_analysis.py::test_cache_normalises_trailing_slash PASSED [ 90%]
tests/test_link_analysis.py::test_cache_invalidate PASSED [ 93%]
tests/test_link_analysis.py::test_your_brand_and_audience_profile_fields_pass_through PASSED [ 96%]
tests/test_link_analysis.py::test_extract_content_does_not_duplicate_nested_text PASSED [100%]
======================== 32 passed, 1 warning in 3.62s ========================
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
| **Local Benchmark Evidence** | **Measured** (8.60s cold; 6,388 total tokens; $0.0074/call) | *Unmeasured in this project* | *Unmeasured in this project* |
| **Official Documentation** | [Google Pricing](https://ai.google.dev/gemini-api/docs/pricing) | [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-6-luna) | [Anthropic Docs](https://platform.claude.com/docs/en/models/haiku-5-5/overview) |

> **Pricing note:** Claude Haiku 5.5 lists a base pricing of $0.10 input / $0.50 output per million tokens for prompts under 100,000 tokens, which rises to $0.50 input / $2.50 output for prompt contexts exceeding 100k tokens.

### B. Selection Rationale

**Selected: Google Gemini 3.5 Flash-Lite**

1. **Assignment Alignment**: Already integrated in the codebase with verified end-to-end execution and schema compliance.
2. **Context Capacity**: 1,048,576 tokens context window easily handles large landing pages and eliminates token boundary issues.
3. **Structured Outputs**: Fully supports strict JSON generation, verified against Pydantic schema validation across 32 tests and live runs.
4. **Cost Assessment**: At **$0.0074 per full 5-section analysis** (3,906 input + 2,482 output tokens, measured), it delivers production-grade business insights at sub-cent cost per request. While GPT-6 Luna lists lower nominal per-token pricing, Gemini 3.5 Flash-Lite is operational, tested, and satisfies all requirements.

---

## Cost Optimization Strategies

| Strategy | Implementation | Evidence & Measured Impact |
|---|---|---|
| **HTML Cleaning & De-duplication** | Strips `<script>`, `<style>`, comments, `<svg>`, `<iframe>`; collects only leaf text blocks so nested wrapper `<div>`s don't repeat their children's text; de-duplicates identical paragraphs | **99.0% reduction measured**: On `stripe.com`, raw HTML was 729,197 bytes (727,926 chars), reduced to 7,589 characters. The leaf-block change alone cut cleaned text from 45,489 to 7,589 chars and prompt tokens from 11,669 to 3,906 (**-67%**) versus the previous extractor, with all five sections still populated. |
| **Hard Truncation Cap** | Caps body extraction at 50,000 characters (~12,500 tokens) | **Prevents runaway token bills** on documentation sites or large single-page applications. |
| **Single-Prompt Consolidation** | Gathers all 5 analysis sections in one LLM call | **80% fewer round-trips**: Avoids repeating system prompts, extraction context, and TLS handshakes across 5 separate calls. |
| **In-Memory TTL Caching** | Serves cached analyses for normalized URLs (`3600s` TTL) | **100% cost reduction on repeats**: Repeat visits within the TTL window resolve in **0.217 ms** with 0 external HTTP/LLM calls. |
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

- [x] **32/32 Unit & Integration Tests Passing**: Verified with pytest.
- [x] **Live Run Evidence**: `live_run.log` and `live_run_output.json` tracked and checked into the repository.
- [x] **Public GitHub Repository**: [github.com/monikakunani/dxora_link_analysis](https://github.com/monikakunani/dxora_link_analysis)
- [ ] **Public Deployment (Optional / Live Demo)**:
  - If deploying to Render, Railway, or Fly.io:
    - Set environment variable `GEMINI_API_KEY` in the hosting dashboard.
    - Provide the live URL (e.g., `https://your-app.onrender.com/` for the UI and `/docs` for the API).
- [ ] **Social Account Verification / Submission Email**: Send the public GitHub repository link and deployed demo link according to the assignment instructions.

---

## License

MIT © 2026 Dxora Link Analysis contributors
