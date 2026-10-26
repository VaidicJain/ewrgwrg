FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application code plus the pre-filled January 2026 database (gridbricks.db).
COPY . .

# The database lives in /data (a volume in docker-compose). On first start the app copies the
# shipped gridbricks.db there, so data written by sync endpoints survives container restarts.
ENV DATABASE_URL=sqlite:////data/gridbricks.db

RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
