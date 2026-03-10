FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini /app/
COPY cli.py /app/cli.py
COPY api /app/api
COPY core /app/core
COPY db /app/db
COPY embeddings /app/embeddings
COPY migrations /app/migrations
COPY pipelines /app/pipelines
COPY scripts /app/scripts
COPY services /app/services
COPY vector /app/vector
COPY data /app/data

RUN pip install --no-cache-dir -e .
RUN chmod +x /app/scripts/bootstrap.sh

EXPOSE 8000

CMD ["/app/scripts/bootstrap.sh"]
