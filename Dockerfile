FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.server.txt .
RUN pip install --no-cache-dir -r requirements.server.txt

# App files
COPY server.py .
COPY static/ ./static/

# Non-root user
RUN useradd -m -u 1000 werwolf && chown -R werwolf:werwolf /app
USER werwolf

EXPOSE 7433

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7433/health || exit 1

CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:7433", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "server:app"]
