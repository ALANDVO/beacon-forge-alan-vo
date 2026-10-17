FROM python:3.12-slim AS base
WORKDIR /app
RUN groupadd -r appuser && useradd -r -g appuser -m appuser
USER appuser

FROM base AS deps
COPY --chown=appuser:appuser backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/lib/python3.12/dist-packages /usr/local/lib/python3.12/dist-packages
COPY --chown=appuser:appuser backend/app ./app
RUN mkdir -p ./data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]