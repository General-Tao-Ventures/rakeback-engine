FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY config.py .
COPY app/ app/
COPY db/ db/
COPY rakeback/ rakeback/
COPY worker/ worker/
COPY scripts/ scripts/

RUN pip install --no-cache-dir -e .

COPY migrations/ migrations/
RUN mkdir -p data

ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["sh", "-c", "python migrations/migrate.py && if [ \"$SEED_SAMPLE_DATA\" = 'true' ] && [ \"$RAKEBACK_ENVIRONMENT\" != 'production' ]; then python scripts/seed_sample_data.py; fi && rakeback-api"]
