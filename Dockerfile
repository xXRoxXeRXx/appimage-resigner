FROM python:3.11-slim

# Metadata
LABEL maintainer="xXRoxXeRXx"
LABEL description="AppImage Re-Signer - GPG signature management for AppImages"
LABEL version="2.0.0"

# Install GPG and cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories BEFORE copying code
RUN mkdir -p uploads signed temp_keys logs && \
    chown -R appuser:appuser uploads signed temp_keys logs

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser web/ ./web/

# Ensure permissions are correct after copy (in case web/ contains logs/)
RUN chown -R appuser:appuser uploads signed temp_keys logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAX_UPLOAD_SIZE_MB=500 \
    SESSION_CLEANUP_HOURS=24 \
    LOG_LEVEL=INFO

# Run the application
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
