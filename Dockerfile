# syntax=docker/dockerfile:1
#
# SVI — Infodemic Surveillance System
# Zero external dependencies: the image installs nothing, because the pipeline
# uses only the Python standard library. That is a design constraint, not an
# accident — it has to run inside locked-down public-sector environments.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="infodemia-svi" \
      org.opencontainers.image.description="Health misinformation surveillance pipeline (zero external dependencies)" \
      org.opencontainers.image.source="https://github.com/MVMLima/infodemia-svi" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/scripts \
    SVI_DB_PATH=/data/infodemia.db

WORKDIR /app

COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY run_pipeline.sh ./

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin svi \
    && mkdir -p /data \
    && chown -R svi:svi /app /data

USER svi
VOLUME ["/data"]

# Default: full pipeline (collect -> analyse -> report), writing to /data.
CMD ["bash", "run_pipeline.sh"]
