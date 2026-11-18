import time
import json
import logging
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from pydantic import ValidationError

from app.config import settings
from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse, ErrorResponse
from app.services.analysis_service import AnalysisService, AnalysisOutputError
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
    docs_url="/docs",
    redoc_url="/redoc",
)

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

@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AI Link Analysis API"}


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
        validated_url = validate_url(url)
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
