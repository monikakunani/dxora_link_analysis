import asyncio
import time
import json
import logging
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from pydantic import ValidationError

from app.config import settings
from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse, ErrorResponse
from app.services.analysis_service import AnalysisService, AnalysisOutputError
from app.services.cache_service import analysis_cache
from app.utils.validators import validate_url, SSRFError, URLValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Website Link Analysis API",
    description=(
        "Analyzes a website URL using LLM to generate business insights, "
        "competitor analysis, SEO recommendations, and target audience identification."
    ),
    version="1.0.0",
    docs_url=None,      # served below with a navigation bar back to the web UI
    redoc_url="/redoc",
)

# Navigation bar injected above Swagger UI so visitors can get back to the app.
_DOCS_NAV = """
<style>
  .app-nav { position: sticky; top: 0; z-index: 10; display: flex; align-items: center; gap: 18px;
    padding: 0 20px; height: 52px; background: #1f2a5a; color: #fff;
    font: 600 14px/1 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  .app-nav .brand { display: flex; align-items: center; gap: 8px; margin-right: auto; }
  .app-nav .mark { width: 18px; height: 18px; border-radius: 5px; background: #7c95ff; }
  .app-nav a { color: #dfe5ff; text-decoration: none; padding: 7px 12px; border-radius: 8px; }
  .app-nav a:hover { background: rgba(255,255,255,.12); color: #fff; }
  .app-nav a.back { background: #7c95ff; color: #0f1115; }
  .app-nav a.back:hover { background: #9aaeff; }
  @media (max-width: 560px) { .app-nav .label { display: none; } }
</style>
<nav class="app-nav" aria-label="Site">
  <span class="brand"><span class="mark"></span><span class="label">Link Analysis &middot; API docs</span></span>
  <a href="/health">Status</a>
  <a class="back" href="/">&larr; Back to analyzer</a>
</nav>
"""


@app.get("/docs", include_in_schema=False)
async def swagger_docs():
    """Swagger UI with a navigation bar linking back to the web UI."""
    page = get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} - API docs")
    html = page.body.decode().replace("<body>", "<body>" + _DOCS_NAV, 1)
    return HTMLResponse(html)

# ---------------------------------------------------------------------------
# Rate-limiting middleware  (pure ASGI — avoids BaseHTTPMiddleware issues)
# ---------------------------------------------------------------------------

class _RateLimitMiddleware:
    """
    Sliding-window rate limiter keyed by client IP.

    Pure ASGI implementation (no BaseHTTPMiddleware) so it works correctly
    with both the production server and the Starlette TestClient.

    Limits each IP to ``calls`` requests per ``period`` seconds.
    Uses an in-memory store; swap for Redis in multi-process deployments.
    """

    def __init__(self, app: ASGIApp, calls: int, period: int) -> None:
        self._app = app
        self._calls = calls
        self._period = period
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        now = time.monotonic()
        window_start = now - self._period

        self._windows[client_ip] = [
            t for t in self._windows[client_ip] if t > window_start
        ]

        if len(self._windows[client_ip]) >= self._calls:
            logger.warning("Rate limit exceeded for IP %s", client_ip)
            body = json.dumps(
                {"detail": "Rate limit exceeded. Please slow down and try again later."}
            ).encode()
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(self._period).encode()),
                    (b"content-length", str(len(body)).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        self._windows[client_ip].append(now)
        await self._app(scope, receive, send)


app.add_middleware(
    _RateLimitMiddleware,
    calls=settings.RATE_LIMIT_CALLS,
    period=settings.RATE_LIMIT_PERIOD,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def web_ui():
    """Browser UI: enter a URL and view the five analysis sections."""
    return FileResponse(_INDEX_HTML, media_type="text/html")


_HEALTH_HTML = Path(__file__).parent / "static" / "health.html"
_STARTED_AT = time.time()


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Health check endpoint.

    Browsers (Accept: text/html) get a readable status page; probes, curl and
    the Docker HEALTHCHECK get JSON.
    """
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(_HEALTH_HTML, media_type="text/html")
    return {
        "status": "healthy",
        "service": "AI Link Analysis API",
        "version": app.version,
        "llm_model": settings.LLM_MODEL,
        "llm_api_key_configured": bool(settings.GEMINI_API_KEY),
        "cached_analyses": analysis_cache.size,
        "uptime_seconds": int(time.time() - _STARTED_AT),
    }


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    tags=["Analysis"],
    summary="Analyze a website URL",
    description="Fetches website content and uses an LLM to generate comprehensive business analysis.",
)
async def link_analysis(request: LinkAnalysisRequest):
    """Analyze a website URL and return structured business insights."""
    url = str(request.url)

    # Validate URL and check for SSRF
    try:
        # DNS resolution is blocking; keep it off the event loop.
        validated_url = await asyncio.to_thread(validate_url, url)
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=f"URL blocked for security reasons: {e}")
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {e}")

    try:
        service = AnalysisService()
        result = await service.analyze(validated_url)
        return result
    except ConnectionError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not access the website: {e}"
        )
    except AnalysisOutputError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValidationError as e:
        logger.warning("Provider output did not satisfy the response schema: %s", e)
        raise HTTPException(
            status_code=502,
            detail="The analysis provider returned data that did not match the required response format.",
        ) from e
    except RuntimeError as e:
        logger.warning("Upstream analysis provider failed: %s", e)
        raise HTTPException(status_code=502, detail="The analysis provider could not complete the request.") from e
    except Exception as e:
        logger.exception("Analysis failed")
        # Surface a missing API key as a clear 500 rather than a generic message
        if "GEMINI_API_KEY" in str(e):
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set. Please add it to your .env file.")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed because an upstream service returned an invalid response."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
