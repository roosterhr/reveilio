FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# antiword gives reliable .doc support; matches the docs/installation.html
# guidance so Docker users aren't worse off than local installs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends antiword \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: install the reveilio library from source. Cached unless
# pyproject.toml or src/ change.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install -e ".[all-db]"

# Layer 2: install the UI-only dependencies (Streamlit, pandas).
COPY ui/requirements.txt ./ui/requirements.txt
RUN pip install -r ui/requirements.txt

# Layer 3: copy the UI source. Invalidates most often but is cheap.
COPY ui/ ./ui/

# Layer 3a: bring the brand logo in from docs/assets (the only file
# allowed through the docs/ exclusion in .dockerignore).
RUN mkdir -p /app/ui/assets
COPY docs/assets/logo.png /app/ui/assets/logo.png

# Named volume in docker-compose mounts here for SQLite persistence.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; \
urllib.request.urlopen('http://localhost:8501/_stcore/health').read()" || exit 1

CMD ["streamlit", "run", "ui/app.py"]
