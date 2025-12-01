# Docker Setup Guide

## Quick Start

### Development

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Production

1. **Copy environment file:**
```bash
cp .env.example .env
```

2. **Adjust values in .env:**
```bash
# Edit .env with production values
nano .env
```

3. **Build and start:**
```bash
docker-compose up -d --build
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | 8000 | Port for the application |
| `MAX_UPLOAD_SIZE_MB` | 500 | Maximum file upload size in MB |
| `SESSION_CLEANUP_HOURS` | 24 | Hours until sessions are cleaned up |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ALLOWED_ORIGINS` | * | CORS allowed origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | false | Allow credentials in CORS requests |

### Resource Limits

Default resource limits in docker-compose.yml:
- **CPU Limit:** 2 cores
- **Memory Limit:** 2GB
- **CPU Reservation:** 0.5 cores
- **Memory Reservation:** 512MB

Adjust in `docker-compose.yml` if needed.

## Security Features

✅ **Non-root User:** Application runs as `appuser` (UID 1000)
✅ **Health Check:** Automatic health monitoring every 30 seconds
✅ **Log Rotation:** 3 log files × 10MB max
✅ **Resource Limits:** CPU and memory constraints

## Volumes

The following directories are mounted:
- `./uploads` - Temporary upload storage
- `./signed` - Signed AppImages
- `./temp_keys` - GPG key storage
- `./logs` - Application logs

## Health Check

The container includes automatic health checks:
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Start Period:** 40 seconds
- **Retries:** 3

Check health status:
```bash
docker-compose ps
```

## Logging

Logs are configured with rotation:
- **Max Size:** 10MB per file
- **Max Files:** 3 files
- **Format:** JSON

View logs:
```bash
# All logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f appimage-resigner
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs appimage-resigner
```

### Permission issues

Ensure directories exist and have correct permissions:
```bash
mkdir -p uploads signed temp_keys logs
chmod 755 uploads signed temp_keys logs
```

### Health check failing

Test endpoint manually:
```bash
curl http://localhost:8000/health
```

### Reset everything

```bash
docker-compose down -v
docker-compose up -d --build
```

## Production Recommendations

1. **Set specific CORS origins:**
   ```bash
   ALLOWED_ORIGINS=https://your-domain.com
   ```

2. **Enable log monitoring:**
   - Use centralized logging (e.g., ELK Stack)
   - Set up alerts for errors

3. **Use reverse proxy:**
   - Nginx or Traefik in front
   - SSL/TLS termination
   - Rate limiting

4. **Backup important data:**
   - Backup `signed/` directory
   - Backup GPG keys in `temp_keys/`

5. **Monitor resource usage:**
   ```bash
   docker stats appimage-resigner
   ```
