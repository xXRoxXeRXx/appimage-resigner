# Docker Deployment Checklist

## ✅ Vor dem Deployment

### Security
- [ ] **SECRET_KEY** generieren und in `.env` setzen
  ```bash
  python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
  ```
- [ ] **CORS_ORIGINS** auf spezifische Domains beschränken
  ```env
  ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  ```
- [ ] **HTTPS** aktivieren (Reverse Proxy: nginx/Apache)
- [ ] **Firewall** Regeln setzen (nur Port 443/80)

### Environment Variables
```env
# Production .env example
SECRET_KEY=<generated-secure-key-min-32-chars>
ALLOWED_ORIGINS=https://yourdomain.com
CORS_ALLOW_CREDENTIALS=true
MAX_UPLOAD_SIZE_MB=500
SESSION_CLEANUP_HOURS=24
LOG_LEVEL=WARNING
```

### Docker Compose Production
```yaml
services:
  appimage-resigner:
    restart: always  # Statt unless-stopped
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    volumes:
      - ./uploads:/app/uploads
      - ./signed:/app/signed
      - ./temp_keys:/app/temp_keys
      - ./logs:/app/logs
```

## 🔍 Bekannte Probleme & Lösungen

### Problem 1: "SECRET_KEY Warnung"
**Symptom:**
```
UserWarning: Using default secret key! Change SECRET_KEY in production!
```

**Lösung:**
1. Generiere einen sicheren Key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Füge zu `.env` hinzu:
   ```env
   SECRET_KEY=<your-generated-key>
   ```
3. Füge zu `docker-compose.yml` hinzu:
   ```yaml
   environment:
     - SECRET_KEY=${SECRET_KEY}
   ```

### Problem 2: "CORS Error in Browser Console"
**Symptom:**
```
Access to fetch at 'http://localhost:8000/api/...' from origin 'https://yourdomain.com' has been blocked by CORS policy
```

**Lösung:**
```env
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Problem 3: "413 Request Entity Too Large" (nginx)
**Symptom:**
```
nginx: 413 Request Entity Too Large
```

**Lösung** - nginx.conf:
```nginx
http {
    client_max_body_size 500M;  # Muss >= MAX_UPLOAD_SIZE_MB sein
}
```

### Problem 4: "Static Files 404"
**Symptom:**
```
GET /static/app.js 404 Not Found
```

**Lösung:**
Prüfe ob `web/static/` Verzeichnis im Container vorhanden ist:
```bash
docker exec appimage-resigner ls -la /app/web/static/
```

Falls nicht, prüfe Dockerfile:
```dockerfile
COPY --chown=appuser:appuser web/ ./web/
```

### Problem 5: "GPG Not Found"
**Symptom:**
```json
{"gpg": {"available": false}}
```

**Lösung:**
Dockerfile muss `gnupg` installieren:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gnupg
```

### Problem 6: "Permission Denied" (Uploads/Signed/Logs)
**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/app/uploads/...'
PermissionError: [Errno 13] Permission denied: '/app/logs/appimage-resigner.log'
```

**Root Cause:**
- Directories created AFTER copying code causes permission conflicts
- COPY --chown doesn't preserve permissions for pre-existing directories

**Solution:**
Dockerfile must create directories BEFORE copying code:
```dockerfile
# CORRECT ORDER:
# 1. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Create directories FIRST
RUN mkdir -p uploads signed temp_keys logs && \
    chown -R appuser:appuser uploads signed temp_keys logs

# 3. Copy code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser web/ ./web/

# 4. Re-ensure permissions after copy
RUN chown -R appuser:appuser uploads signed temp_keys logs

# 5. Switch to non-root user
USER appuser
```

**Verification:**
```bash
docker exec appimage-resigner ls -la /app/logs/
# Should show: drwxrwxrwx ... appuser appuser
docker exec appimage-resigner touch /app/logs/test.txt
# Should succeed without errors
```

### Problem 7: "Module Not Found" (Python Import Error)
**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Lösung:**
1. Prüfe `requirements.txt` ist aktuell
2. Rebuild ohne Cache:
   ```bash
   docker-compose build --no-cache
   ```

### Problem 8: "Health Check Failing"
**Symptom:**
```
docker ps  # STATUS: unhealthy
```

**Lösung:**
1. Prüfe Logs:
   ```bash
   docker logs appimage-resigner --tail 50
   ```
2. Health-Check manuell testen:
   ```bash
   docker exec appimage-resigner curl http://localhost:8000/health
   ```
3. Dockerfile HEALTHCHECK Timeout erhöhen:
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3
   ```

### Problem 9: "docker-compose KeyError: 'id'" (Harmlos)
**Symptom:**
```
Exception in thread Thread-4 (watch_events):
...
KeyError: 'id'
```

**Root Cause:**
- Known bug in docker-compose event streaming (threading race condition)
- Occurs in docker-compose versions < 2.0
- Does NOT affect container operation

**Solution:**
- ✅ **Ignore this error** - container runs normally
- Verify container is healthy: `docker ps`
- Check logs: `docker logs appimage-resigner`
- Upgrade docker-compose (optional):
  ```bash
  # Linux
  sudo apt-get update && sudo apt-get install docker-compose-plugin
  
  # Or use Docker Compose V2
  docker compose up -d  # Note: 'compose' not 'docker-compose'
  ```

**Verification:**
```bash
docker ps --filter "name=appimage-resigner"
# Should show: STATUS: Up X minutes (healthy)
```

## 🧪 Testing Checklist

### Lokal testen
```bash
# 1. Build
docker-compose build

# 2. Start
docker-compose up -d

# 3. Check Status
docker ps
docker logs appimage-resigner

# 4. Test Health
curl http://localhost:8000/health

# 5. Test Frontend
curl http://localhost:8000/static/index.html

# 6. Test API
curl -X POST http://localhost:8000/api/session/create
```

### Production Pre-Flight
```bash
# 1. Environment Variables
docker exec appimage-resigner env | grep SECRET_KEY

# 2. GPG Available
docker exec appimage-resigner gpg --version

# 3. Directories Writable
docker exec appimage-resigner ls -la /app/

# 4. Disk Space
docker exec appimage-resigner df -h

# 5. Memory Usage
docker stats appimage-resigner --no-stream
```

## 📊 Monitoring

### Wichtige Metriken
- **Container Status**: `docker ps` → healthy/unhealthy
- **CPU/Memory**: `docker stats appimage-resigner`
- **Logs**: `docker logs -f appimage-resigner`
- **Disk Space**: `docker exec appimage-resigner df -h`

### Log-Analyse
```bash
# Fehler finden
docker logs appimage-resigner 2>&1 | grep -i error

# Warnungen finden
docker logs appimage-resigner 2>&1 | grep -i warn

# Letzte 100 Zeilen
docker logs appimage-resigner --tail 100

# Follow Logs
docker logs -f appimage-resigner
```

## 🔧 Troubleshooting Commands

```bash
# Container neu starten
docker-compose restart

# Container neu bauen
docker-compose build --no-cache && docker-compose up -d

# In Container einloggen
docker exec -it appimage-resigner /bin/bash

# Environment Variables anzeigen
docker exec appimage-resigner env

# Python Packages prüfen
docker exec appimage-resigner pip list

# Netzwerk testen
docker network ls
docker network inspect appimage-resigner_default

# Volumes prüfen
docker volume ls
```

## 📝 Production Deployment

### Mit nginx Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket Support (falls benötigt)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Systemd Service (Alternative)
```ini
[Unit]
Description=AppImage Re-Signer Docker Container
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/appimage-resigner
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

## 🎯 Quick Reference

### Start/Stop
```bash
docker-compose up -d      # Start
docker-compose down       # Stop & Remove
docker-compose restart    # Restart
docker-compose logs -f    # Follow Logs
```

### Update
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Backup
```bash
# Backup Volumes
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ signed/ temp_keys/ logs/

# Backup Database (falls verwendet)
docker exec appimage-resigner pg_dump ...
```

---

**Created**: 2025-12-01
**Last Updated**: 2025-12-01
**Maintainer**: xXRoxXeRXx
