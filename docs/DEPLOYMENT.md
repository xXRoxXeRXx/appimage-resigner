# AppImage Re-Signer - Deployment Guide

**Version:** 2.0.0  
**Last Updated:** 2025-12-01

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Manual Installation](#manual-installation)
4. [Production Setup](#production-setup)
5. [Reverse Proxy Configuration](#reverse-proxy-configuration)
6. [SSL/TLS Setup](#ssltls-setup)
7. [Environment Variables](#environment-variables)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Development (Local)

```bash
# Clone repository
git clone https://github.com/xXRoxXeRXx/appimage-resigner.git
cd appimage-resigner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Start server
python web/app.py
# or
uvicorn web.app:app --reload --port 8000
```

Access: http://localhost:8000

---

## Docker Deployment

### Using Docker Compose (Recommended)

**1. Clone repository**

```bash
git clone https://github.com/xXRoxXeRXx/appimage-resigner.git
cd appimage-resigner
```

**2. Create `.env` file**

```bash
cp .env.example .env
# Edit .env with your settings
```

**3. Build and start**

```bash
docker-compose up -d
```

**4. Check status**

```bash
docker-compose ps
docker-compose logs -f
```

Access: http://localhost:8000

**5. Stop**

```bash
docker-compose down
```

### Using Docker (Standalone)

**1. Build image**

```bash
docker build -t appimage-resigner:latest .
```

**2. Run container**

```bash
docker run -d \
  --name appimage-resigner \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/signed:/app/signed \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  appimage-resigner:latest
```

**3. Check logs**

```bash
docker logs -f appimage-resigner
```

**4. Stop**

```bash
docker stop appimage-resigner
docker rm appimage-resigner
```

### Docker Image Optimization

**Multi-stage Build** (`Dockerfile`):

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install GPG
RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

WORKDIR /app

# Copy application
COPY --chown=appuser:appuser . .

# Create directories
RUN mkdir -p uploads signed temp_keys logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Size Comparison:**
- Original: ~800 MB
- Optimized: ~300 MB

---

## Manual Installation

### System Requirements

- **OS:** Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- **Python:** 3.9+ (3.11 recommended)
- **GPG:** 2.2+
- **RAM:** 1 GB minimum, 2 GB recommended
- **Disk:** 5 GB free space

### Ubuntu/Debian

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install GPG
sudo apt install -y gnupg

# Install Git
sudo apt install -y git

# Clone repository
git clone https://github.com/xXRoxXeRXx/appimage-resigner.git
cd appimage-resigner

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p uploads signed temp_keys logs

# Create .env file
cp .env.example .env
nano .env  # Edit configuration

# Test installation
python -c "import gnupg; print(f'GPG version: {gnupg.GPG().version}')"
```

### RHEL/CentOS/Fedora

```bash
# Update system
sudo dnf update -y

# Install Python 3.11
sudo dnf install -y python3.11 python3.11-pip

# Install GPG (usually pre-installed)
sudo dnf install -y gnupg2

# Install Git
sudo dnf install -y git

# Follow same steps as Ubuntu from "Clone repository"
```

---

## Production Setup

### Systemd Service

Create `/etc/systemd/system/appimage-resigner.service`:

```ini
[Unit]
Description=AppImage Re-Signer Web Service
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/appimage-resigner
Environment="PATH=/opt/appimage-resigner/venv/bin"
EnvironmentFile=/opt/appimage-resigner/.env
ExecStart=/opt/appimage-resigner/venv/bin/uvicorn web.app:app --host 127.0.0.1 --port 8000 --workers 4

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/appimage-resigner/uploads /opt/appimage-resigner/signed /opt/appimage-resigner/logs

# Restart policy
Restart=on-failure
RestartSec=10s

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable appimage-resigner
sudo systemctl start appimage-resigner
sudo systemctl status appimage-resigner
```

**View logs:**

```bash
sudo journalctl -u appimage-resigner -f
```

### Gunicorn (Alternative)

Install Gunicorn:

```bash
pip install gunicorn
```

Create `gunicorn.conf.py`:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
timeout = 120
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
```

Start with Gunicorn:

```bash
gunicorn web.app:app -c gunicorn.conf.py
```

---

## Reverse Proxy Configuration

### Nginx (Recommended)

**1. Install Nginx**

```bash
sudo apt install -y nginx
```

**2. Create configuration** `/etc/nginx/sites-available/appimage-resigner`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=5r/s;

# Upstream
upstream appimage_backend {
    server 127.0.0.1:8000 fail_timeout=10s max_fails=3;
}

server {
    listen 80;
    listen [::]:80;
    server_name appimage-resigner.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name appimage-resigner.yourdomain.com;

    # SSL Configuration (see SSL/TLS Setup section)
    ssl_certificate /etc/letsencrypt/live/appimage-resigner.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/appimage-resigner.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Client body size (for large AppImage files)
    client_max_body_size 500M;
    client_body_timeout 300s;

    # Timeouts
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Logging
    access_log /var/log/nginx/appimage-resigner-access.log;
    error_log /var/log/nginx/appimage-resigner-error.log warn;

    # Root location
    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://appimage_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for future use)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Upload endpoints (stricter rate limiting)
    location ~ ^/api/(upload|sign) {
        limit_req zone=upload_limit burst=5 nodelay;

        proxy_pass http://appimage_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Longer timeout for uploads
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    # Static files (cache)
    location /static/ {
        alias /opt/appimage-resigner/web/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Health check (no rate limit)
    location /health {
        proxy_pass http://appimage_backend;
        access_log off;
    }
}
```

**3. Enable and test**

```bash
# Test configuration
sudo nginx -t

# Enable site
sudo ln -s /etc/nginx/sites-available/appimage-resigner /etc/nginx/sites-enabled/

# Reload Nginx
sudo systemctl reload nginx
```

### Apache (Alternative)

**Install Apache and modules:**

```bash
sudo apt install -y apache2 libapache2-mod-proxy-html
sudo a2enmod proxy proxy_http proxy_wstunnel ssl headers rewrite
```

**Configuration** `/etc/apache2/sites-available/appimage-resigner.conf`:

```apache
<VirtualHost *:80>
    ServerName appimage-resigner.yourdomain.com
    Redirect permanent / https://appimage-resigner.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName appimage-resigner.yourdomain.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/appimage-resigner.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/appimage-resigner.yourdomain.com/privkey.pem

    # Security Headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"

    # Proxy settings
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Timeout for large uploads
    ProxyTimeout 300

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/appimage-resigner-error.log
    CustomLog ${APACHE_LOG_DIR}/appimage-resigner-access.log combined
</VirtualHost>
```

---

## SSL/TLS Setup

### Let's Encrypt (Free, Automated)

**1. Install Certbot**

```bash
sudo apt install -y certbot python3-certbot-nginx
```

**2. Obtain certificate**

```bash
sudo certbot --nginx -d appimage-resigner.yourdomain.com
```

**3. Auto-renewal**

Certbot adds a cron job automatically. Test renewal:

```bash
sudo certbot renew --dry-run
```

### Self-Signed Certificate (Development)

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/appimage-resigner.key \
  -out /etc/ssl/certs/appimage-resigner.crt \
  -subj "/CN=appimage-resigner.local"
```

Update Nginx configuration to use these certificates.

---

## Environment Variables

### Production `.env` Template

```ini
# Application
APP_NAME=AppImage Re-Signer
VERSION=2.0.0

# Server
HOST=127.0.0.1
PORT=8000
DEBUG=false

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
CORS_ORIGINS=https://appimage-resigner.yourdomain.com

# File Limits
MAX_FILE_SIZE_MB=500

# Session Management
CLEANUP_AFTER_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_TO_CONSOLE=false

# GPG (optional)
GPG_BINARY_PATH=/usr/bin/gpg

# Paths (if not using default)
UPLOAD_DIR=/opt/appimage-resigner/uploads
SIGNED_DIR=/opt/appimage-resigner/signed
TEMP_KEYS_DIR=/opt/appimage-resigner/temp_keys
LOG_DIR=/opt/appimage-resigner/logs
```

### Generate SECRET_KEY

```bash
openssl rand -hex 32
```

### Docker Environment

For Docker, create `.env` in project root. Docker Compose will automatically use it.

For standalone Docker:

```bash
docker run --env-file .env ...
```

---

## Monitoring & Logging

### Application Logs

**Location:** `logs/appimage-resigner.log`

**Log Format:**
```
2025-12-01 10:30:15 | INFO     | web.app | create_session:180 | Session created | session_id=550e8400...
```

**Log Rotation:**
- Max file size: 10 MB
- Backup count: 10 files
- Total max: 100 MB

**View logs:**

```bash
# Tail logs
tail -f logs/appimage-resigner.log

# Search logs
grep "ERROR" logs/appimage-resigner.log

# Count errors today
grep "$(date +%Y-%m-%d)" logs/appimage-resigner.log | grep "ERROR" | wc -l
```

### Systemd Journal

```bash
# View service logs
sudo journalctl -u appimage-resigner -f

# Last 100 lines
sudo journalctl -u appimage-resigner -n 100

# Errors only
sudo journalctl -u appimage-resigner -p err

# Since boot
sudo journalctl -u appimage-resigner -b
```

### Nginx Logs

```bash
# Access log
tail -f /var/log/nginx/appimage-resigner-access.log

# Error log
tail -f /var/log/nginx/appimage-resigner-error.log

# Count 5xx errors
grep " 5[0-9][0-9] " /var/log/nginx/appimage-resigner-access.log | wc -l
```

### Health Check Monitoring

**Script:** `scripts/health_check.sh`

```bash
#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
TIMEOUT=10

response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$HEALTH_URL")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" -eq 200 ]; then
    echo "✓ Service is healthy"
    echo "$body" | jq .
    exit 0
else
    echo "✗ Service is unhealthy (HTTP $http_code)"
    exit 1
fi
```

**Cron job** (check every 5 minutes):

```bash
*/5 * * * * /opt/appimage-resigner/scripts/health_check.sh >> /var/log/appimage-health.log 2>&1
```

### Prometheus Metrics (Future)

Install dependencies:

```bash
pip install prometheus-client
```

Add to `web/app.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

signatures_total = Counter('appimage_signatures_total', 'Total signatures created')
signing_duration = Histogram('appimage_signing_duration_seconds', 'Signing duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## Backup & Recovery

### Files to Backup

1. **Configuration:**
   - `.env`
   - `web/core/config.py`

2. **User Data:**
   - `uploads/` (optional, temporary)
   - `signed/` (important)
   - `logs/`

3. **GPG Keys:**
   - `temp_keys/` (optional, temporary)
   - System GPG keyring (if using system keys)

### Backup Script

```bash
#!/bin/bash

BACKUP_DIR="/backups/appimage-resigner"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_FILE" \
    .env \
    signed/ \
    logs/ \
    --exclude='*.tmp'

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/backup_*.tar.gz | tail -n +31 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
```

**Cron job** (daily at 2 AM):

```bash
0 2 * * * /opt/appimage-resigner/scripts/backup.sh
```

### Restore

```bash
cd /opt/appimage-resigner
tar -xzf /backups/appimage-resigner/backup_20251201_020000.tar.gz
sudo systemctl restart appimage-resigner
```

---

## Troubleshooting

### Service won't start

**Check logs:**
```bash
sudo systemctl status appimage-resigner
sudo journalctl -u appimage-resigner -n 50
```

**Common issues:**
- Port 8000 already in use: `sudo netstat -tulpn | grep 8000`
- Permission denied: Check file ownership and permissions
- Python not found: Verify virtual environment path in systemd service

### Upload fails

**Error:** "Invalid AppImage: Not an ELF file"

**Solution:** Ensure file is a valid AppImage:
```bash
file MyApp.AppImage
# Should output: ELF 64-bit LSB executable
```

**Error:** "File size exceeds limit"

**Solution:** Increase `MAX_FILE_SIZE_MB` in `.env` and `client_max_body_size` in Nginx.

### Signing fails

**Error:** "gpg: signing failed: Bad passphrase"

**Solution:**
- Verify passphrase is correct
- Check key has signing capability: `gpg --list-keys KEY_ID`
- Ensure key is not expired

**Error:** "GPG not found"

**Solution:**
```bash
# Check GPG installation
which gpg
gpg --version

# Install if missing
sudo apt install gnupg
```

### High memory usage

**Cause:** Large AppImage files (>500 MB)

**Solution:**
- Implement streaming upload/download
- Increase system memory
- Set worker/process limits

### Slow performance

**Optimization:**
- Use Gunicorn with multiple workers: `--workers 4`
- Enable Nginx caching for static files
- Use Redis for session storage (future)
- Monitor with `htop` or `top`

---

## Performance Tuning

### Uvicorn Workers

```bash
uvicorn web.app:app --host 127.0.0.1 --port 8000 --workers 4
```

**Worker count:** `(2 x CPU cores) + 1`

### Nginx Tuning

```nginx
worker_processes auto;
worker_connections 1024;

# Keepalive
keepalive_timeout 65;
keepalive_requests 100;

# Buffers
client_body_buffer_size 128k;
client_header_buffer_size 1k;
large_client_header_buffers 4 4k;
```

### System Limits

Increase file descriptors in `/etc/security/limits.conf`:

```
appuser soft nofile 65536
appuser hard nofile 65536
```

---

## Security Checklist

- [ ] HTTPS enabled with valid certificate
- [ ] CORS configured with specific origins
- [ ] Rate limiting enabled (Nginx)
- [ ] Security headers set (CSP, HSTS, X-Frame-Options)
- [ ] Non-root user running service
- [ ] File size limits enforced
- [ ] Secret key generated and secured
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] Logs monitored for suspicious activity
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular backups scheduled
- [ ] System updates automated
- [ ] Intrusion detection installed (fail2ban)
- [ ] Audit logging enabled

---

## Support & Updates

**Documentation:** https://github.com/xXRoxXeRXx/appimage-resigner/docs  
**Issues:** https://github.com/xXRoxXeRXx/appimage-resigner/issues  
**Releases:** https://github.com/xXRoxXeRXx/appimage-resigner/releases

**Update Procedure:**

```bash
cd /opt/appimage-resigner
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart appimage-resigner
```

---

**Last Updated:** 2025-12-01  
**Version:** 2.0.0
