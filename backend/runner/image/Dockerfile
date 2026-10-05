# Candidate runtime image for BenchProof local isolated runs (development alternate).
# Base pinned by digest below after `docker pull`; versions match backend/requirements.lock.txt.
FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi==0.142.2 pydantic==2.13.5 httpx==0.28.1
RUN useradd --uid 65534 --no-create-home candidate 2>/dev/null || true
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
