FROM python:3.11-slim

# Metadata
LABEL maintainer="xXRoxXeRXx"
LABEL description="AppImage Re-Signer - GPG signature management for AppImages"
LABEL version="2.0.0"

# Install GPG and cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    ca-certificates \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -m -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories BEFORE copying code
RUN mkdir -p uploads signed temp_keys logs /home/appuser/.gnupg && \
    chown -R appuser:appuser uploads signed temp_keys logs /home/appuser/.gnupg && \
    chmod 700 /home/appuser/.gnupg

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser web/ ./web/

# Copy and set executable permission for entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Ensure permissions are correct after copy (in case web/ contains logs/)
RUN chown -R appuser:appuser uploads signed temp_keys logs

# NOTE: Do NOT switch to appuser here - entrypoint needs root for chown
# The entrypoint script will switch to appuser after fixing permissions

# Set entrypoint (runs as root, then drops to appuser)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

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
