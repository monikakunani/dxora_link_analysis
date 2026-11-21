# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install dependencies into a virtual environment for a clean final image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

LABEL maintainer="dxora"
LABEL description="AI-Powered Website Link Analysis API"

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY --chown=app:app app/ ./app/

# Hosting platforms (Render, Railway, Fly.io, Cloud Run) inject $PORT; default 4000 locally.
ENV PORT=4000
EXPOSE 4000

USER app

# Health check — calls the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; import os; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT', '4000'))" \
    || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-4000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
