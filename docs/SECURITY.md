# AppImage Re-Signer - Security Guide

**Version:** 2.0.0  
**Last Updated:** 2025-12-01

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Threat Model](#threat-model)
3. [Security Best Practices](#security-best-practices)
4. [Vulnerability Reporting](#vulnerability-reporting)
5. [Production Security Checklist](#production-security-checklist)
6. [CORS Configuration](#cors-configuration)
7. [Content Security Policy (CSP)](#content-security-policy-csp)
8. [HTTPS & TLS](#https--tls)
9. [Input Validation](#input-validation)
10. [Authentication & Authorization](#authentication--authorization)
11. [Session Security](#session-security)
12. [File Upload Security](#file-upload-security)
13. [GPG Key Security](#gpg-key-security)
14. [Rate Limiting](#rate-limiting)
15. [Audit Logging](#audit-logging)
16. [Security Headers](#security-headers)
17. [Dependency Security](#dependency-security)

---

## Security Overview

AppImage Re-Signer handles sensitive cryptographic operations and file uploads. This guide provides comprehensive security recommendations for deployment and operation.

**Security Principles:**
- **Defense in Depth** - Multiple layers of security
- **Least Privilege** - Minimal permissions required
- **Fail Secure** - Safe defaults, explicit security
- **Assume Breach** - Monitor and detect compromises
- **Security by Design** - Built-in from the start

---

## Threat Model

### Assets to Protect

1. **GPG Private Keys** - Most sensitive
2. **Passphrases** - Credential exposure
3. **Uploaded AppImages** - Potential malware
4. **Signed AppImages** - Integrity critical
5. **Session Data** - Privacy concern
6. **Application Configuration** - Secret exposure
7. **Logs** - Information disclosure

### Threat Actors

1. **External Attackers** - Internet-facing threats
2. **Malicious Users** - Abuse of legitimate access
3. **Compromised Dependencies** - Supply chain attacks
4. **Insider Threats** - Authorized user abuse
5. **Automated Bots** - Scanning & exploitation

### Attack Vectors

1. **Malicious File Upload** - Malware, path traversal
2. **Credential Theft** - Passphrase interception
3. **Session Hijacking** - Cookie/token theft
4. **Denial of Service** - Resource exhaustion
5. **Code Injection** - Command injection, XSS
6. **Man-in-the-Middle** - Network interception
7. **Dependency Vulnerabilities** - Known CVEs

---

## Security Best Practices

### Development

**1. Secure Coding**
- Input validation at all entry points
- Output encoding for user-controlled data
- Parameterized queries (when using databases)
- Avoid `eval()` and dynamic code execution
- Use safe string formatting

**2. Secret Management**
```python
# ❌ BAD - Hardcoded secrets
SECRET_KEY = "mysecretkey123"

# ✅ GOOD - Environment variables
from web.core.config import settings
SECRET_KEY = settings.secret_key
```

**3. Error Handling**
```python
# ❌ BAD - Exposing stack traces
except Exception as e:
    return {"error": str(e)}

# ✅ GOOD - Generic error messages
except Exception as e:
    logger.error(f"Signing failed | error={str(e)}")
    return {"error": "Signing operation failed"}
```

**4. Logging**
```python
# ❌ BAD - Logging sensitive data
logger.info(f"User passphrase: {passphrase}")

# ✅ GOOD - Redacted logging
logger.info(f"User authentication attempt | user_id={user_id}")
```

### Deployment

**1. HTTPS Only**
- Always use TLS/SSL in production
- Redirect HTTP to HTTPS
- Use HSTS headers

**2. Firewall Configuration**
```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

**3. System Hardening**
- Keep system updated
- Disable unnecessary services
- Use fail2ban for brute force protection
- Enable SELinux/AppArmor

**4. Container Security**
- Run as non-root user
- Use minimal base images
- Scan for vulnerabilities
- Limit resource usage

---

## Vulnerability Reporting

### Responsible Disclosure

If you discover a security vulnerability, please report it responsibly:

**Contact:**
- **Email:** security@yourdomain.com (preferred)
- **GitHub:** Create a private security advisory
- **PGP Key:** Available at https://yourdomain.com/.well-known/pgp-key.txt

**Please include:**
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

**Response Timeline:**
- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Fix Timeline:** Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: Next release

**Disclosure Policy:**
- We request a 90-day disclosure period
- Public disclosure after fix is released
- Credit given to reporter (if desired)

### Security Advisories

Security updates are published:
- GitHub Security Advisories
- Release Notes with `[SECURITY]` tag
- Email notification to users (if applicable)

### Bug Bounty

Currently, we do not offer a bug bounty program. However, we deeply appreciate responsible disclosure and will:
- Acknowledge your contribution
- Credit you in release notes (if desired)
- Consider donations/sponsorship

---

## Production Security Checklist

### Pre-Deployment

- [ ] **HTTPS configured** with valid certificate
- [ ] **CORS origins** set to specific domains (not `*`)
- [ ] **CSP headers** configured
- [ ] **Security headers** enabled (HSTS, X-Frame-Options, etc.)
- [ ] **Debug mode disabled** (`DEBUG=false`)
- [ ] **Secret key** generated (32+ characters, random)
- [ ] **Rate limiting** enabled on all endpoints
- [ ] **File size limits** enforced
- [ ] **Input validation** on all user inputs
- [ ] **Error messages** are generic (no stack traces)
- [ ] **Logging** configured (no sensitive data logged)
- [ ] **Firewall** configured (minimal open ports)
- [ ] **System updated** (OS, Python, dependencies)
- [ ] **Non-root user** running application
- [ ] **File permissions** correctly set
- [ ] **Backup system** in place
- [ ] **Monitoring** enabled
- [ ] **Intrusion detection** configured (fail2ban)

### Post-Deployment

- [ ] **Health check** endpoint accessible
- [ ] **Logs monitored** for suspicious activity
- [ ] **Security scans** scheduled (weekly)
- [ ] **Dependency updates** automated (Dependabot)
- [ ] **Backup tested** (restore procedure verified)
- [ ] **Incident response plan** documented
- [ ] **Access logs reviewed** regularly
- [ ] **SSL certificate expiry** monitored

### Periodic Review

- [ ] **Security audit** (quarterly)
- [ ] **Penetration testing** (annually)
- [ ] **Dependency audit** (monthly)
- [ ] **Log analysis** (weekly)
- [ ] **Access review** (quarterly)
- [ ] **Policy update** (annually)

---

## CORS Configuration

### Current Implementation

```python
from fastapi.middleware.cors import CORSMiddleware
from web.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Environment Configuration

```bash
# .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Best Practices

**✅ DO:**
- Use specific origins (not `*`)
- Use HTTPS URLs only
- Whitelist required methods only
- Validate Origin header

**❌ DON'T:**
- Use `allow_origins=["*"]` in production
- Allow credentials with wildcard origins
- Allow all methods if not needed
- Trust client-provided Origin header without validation

### Advanced Configuration

```python
# Stricter CORS for production
from fastapi import Request

@app.middleware("http")
async def validate_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    allowed = settings.cors_origins_list
    
    if origin and origin not in allowed:
        logger.warning(f"Blocked request from unauthorized origin | origin={origin}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Origin not allowed"}
        )
    
    response = await call_next(request)
    return response
```

---

## Content Security Policy (CSP)

### Implementation

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    return response
```

### Directive Explanation

| Directive | Value | Purpose |
|-----------|-------|---------|
| `default-src` | `'self'` | Default policy for all resources |
| `script-src` | `'self' 'unsafe-inline'` | Allow inline scripts (for app.js) |
| `style-src` | `'self' 'unsafe-inline'` | Allow inline styles (for style.css) |
| `img-src` | `'self' data:` | Allow images and data URIs |
| `connect-src` | `'self'` | API requests to same origin only |
| `frame-ancestors` | `'none'` | Prevent clickjacking |
| `form-action` | `'self'` | Forms submit to same origin only |

### Removing `unsafe-inline`

For better security, remove `unsafe-inline`:

1. **Move inline scripts to files:**
```html
<!-- Before -->
<script>
  console.log('Hello');
</script>

<!-- After -->
<script src="/static/app.js"></script>
```

2. **Use nonces for dynamic scripts:**
```python
import secrets

@app.get("/")
async def root():
    nonce = secrets.token_urlsafe(16)
    # Pass nonce to template
    # Add to CSP: script-src 'nonce-{nonce}'
```

---

## HTTPS & TLS

### TLS Configuration

**Recommended Settings (Nginx):**

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;

ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### Certificate Management

**1. Let's Encrypt (Automated):**
```bash
sudo certbot --nginx -d appimage-resigner.yourdomain.com
```

**2. Certificate Monitoring:**
```bash
#!/bin/bash
# Check certificate expiry
DAYS_LEFT=$(openssl s_client -connect appimage-resigner.yourdomain.com:443 -servername appimage-resigner.yourdomain.com </dev/null 2>/dev/null | openssl x509 -noout -checkend $((30*86400)))

if [ $? -eq 1 ]; then
    echo "Certificate expires in less than 30 days!" | mail -s "SSL Alert" admin@yourdomain.com
fi
```

### HSTS (HTTP Strict Transport Security)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

**HSTS Preload List:**
Submit your domain to https://hstspreload.org/ for browser-level enforcement.

---

## Input Validation

### File Upload Validation

**Current Implementation:**

```python
from web.core.validation import validate_appimage_file

# ELF Header Check
def validate_elf_header(file_path: Path) -> Tuple[bool, Optional[str]]:
    ELF_MAGIC = b'\x7fELF'
    
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        
    if magic != ELF_MAGIC:
        return False, "Not an ELF file (invalid magic bytes)"
    
    return True, None

# AppImage Format Check
def validate_appimage_format(file_path: Path) -> Tuple[bool, Optional[str]]:
    APPIMAGE_TYPE2_MAGIC = b'AI\x02'
    
    with open(file_path, 'rb') as f:
        f.seek(8)
        magic = f.read(3)
        
    if magic != APPIMAGE_TYPE2_MAGIC:
        return False, "Not an AppImage Type 2 format"
    
    return True, None
```

### Path Traversal Prevention

```python
from pathlib import Path

def safe_file_path(base_dir: Path, filename: str) -> Path:
    """Prevent path traversal attacks"""
    # Remove directory components
    safe_name = Path(filename).name
    
    # Resolve to absolute path
    file_path = (base_dir / safe_name).resolve()
    
    # Ensure path is within base_dir
    if not str(file_path).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal detected")
    
    return file_path
```

### Command Injection Prevention

```python
import shlex

# ❌ BAD - Shell injection possible
os.system(f"gpg --sign {filename}")

# ✅ GOOD - Use list arguments
subprocess.run(["gpg", "--sign", filename])

# ✅ GOOD - Shell escaping if needed
safe_filename = shlex.quote(filename)
subprocess.run(f"gpg --sign {safe_filename}", shell=True)
```

### XSS Prevention

```python
# ❌ BAD - No escaping
return f"<p>Welcome {username}</p>"

# ✅ GOOD - HTML escaping
import html
return f"<p>Welcome {html.escape(username)}</p>"

# ✅ BETTER - Use templating engine (Jinja2)
return templates.TemplateResponse("welcome.html", {"username": username})
```

---

## Authentication & Authorization

### Future Implementation

Currently, the application does not implement authentication. For production:

**Option 1: API Keys**

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/api/sign")
async def sign_appimage(api_key: str = Depends(get_api_key)):
    # Protected endpoint
    ...
```

**Option 2: OAuth 2.0**

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/api/sign")
async def sign_appimage(token: str = Depends(oauth2_scheme)):
    # Verify JWT token
    ...
```

**Option 3: mTLS (Mutual TLS)**

Client certificates for machine-to-machine authentication.

---

## Session Security

### Current Implementation

```python
# In-memory sessions (not persistent)
sessions = {}

class SigningSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        # No passphrase storage
        # No GPG key storage beyond temporary files
```

### Security Features

1. **No Passphrase Storage** - Passphrases are overwritten after use
2. **Automatic Cleanup** - Sessions deleted after 24 hours
3. **File Cleanup** - Temporary files deleted with session
4. **UUID Session IDs** - Cryptographically random

### Future: Redis Sessions

```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def create_session(session_id: str):
    session_data = {
        "created_at": datetime.now().isoformat(),
        "status": "initialized"
    }
    redis_client.setex(
        f"session:{session_id}",
        timedelta(hours=24),
        json.dumps(session_data)
    )
```

---

## File Upload Security

### Size Limits

```python
# web/core/config.py
MAX_FILE_SIZE_MB = 500
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Enforcement
def validate_file_size(file_path: Path, max_size_bytes: int) -> Tuple[bool, Optional[str]]:
    file_size = file_path.stat().st_size
    
    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        max_mb = max_size_bytes / (1024 * 1024)
        return False, f"File too large ({size_mb:.2f} MB > {max_mb} MB)"
    
    return True, None
```

### Virus Scanning (Future)

```python
import clamd

def scan_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Scan file with ClamAV"""
    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.scan(str(file_path))
        
        if result and 'FOUND' in result[str(file_path)]:
            virus_name = result[str(file_path)][1]
            return False, f"Virus detected: {virus_name}"
        
        return True, None
    except Exception as e:
        logger.error(f"Virus scan failed | error={str(e)}")
        # Fail secure: reject file if scan fails
        return False, "Unable to scan file"
```

### Temporary File Handling

```python
import tempfile

# ✅ GOOD - Auto-cleanup
with tempfile.NamedTemporaryFile(mode='w+b', suffix='.zip', delete=True) as tmp:
    # Use tmp.name
    ...
# File automatically deleted
```

---

## GPG Key Security

### Passphrase Handling

**Security Measures:**

1. **No Storage** - Never stored in sessions or logs
2. **Memory Overwriting** - Overwritten after use
3. **Validation** - Empty passphrases rejected
4. **Transmission** - Only via HTTPS

```python
# After signing
if passphrase:
    passphrase = "X" * len(passphrase)  # Overwrite
    del passphrase                       # Delete reference
```

### Key File Handling

1. **Temporary Storage** - Stored in `temp_keys/` directory
2. **Session-Scoped** - Unique to each session
3. **Automatic Deletion** - Deleted after signing or session cleanup
4. **No System Keyring** - Keys not imported to system keyring (if uploaded)

### Hardware Token Support (Future)

```python
# YubiKey/GPG Smart Card support
def sign_with_hardware_token(appimage_path: str, key_id: str):
    # GPG automatically uses hardware token
    gpg.sign_file(
        open(appimage_path, 'rb'),
        keyid=key_id,
        detach=True,
        output=f"{appimage_path}.asc"
    )
```

---

## Rate Limiting

### Implementation with slowapi

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/upload/appimage")
@limiter.limit("10/minute")
async def upload_appimage(request: Request, ...):
    ...

@app.post("/api/sign")
@limiter.limit("5/minute")
async def sign_appimage(request: Request, ...):
    ...
```

### Nginx Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=5r/s;

location /api/upload/ {
    limit_req zone=upload_limit burst=5 nodelay;
    ...
}
```

---

## Audit Logging

### What to Log

**✅ DO Log:**
- Session creation/deletion
- File uploads (filename, size, IP)
- Signing operations (key ID, success/failure)
- Verification attempts
- Downloads (session ID, IP)
- Failed authentication attempts
- Rate limit violations
- Security exceptions

**❌ DON'T Log:**
- Passphrases
- Private keys
- Session tokens
- Personally identifiable information (PII)

### Log Format

```
2025-12-01 10:30:15 | INFO     | web.app | sign_appimage:420 | Signing completed | session_id=550e8400... | key_id=C407155E5D49FE6B | ip=192.168.1.100
```

### Log Monitoring

```bash
# Monitor for suspicious activity
grep "ERROR\|WARN\|CRITICAL" logs/appimage-resigner.log

# Count failed signing attempts
grep "Signing failed" logs/appimage-resigner.log | wc -l

# Monitor from specific IP
grep "ip=192.168.1.100" logs/appimage-resigner.log
```

---

## Security Headers

### Implementation

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # HSTS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # XSS Protection (legacy, but still good)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response
```

### Header Explanation

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000` | Force HTTPS for 1 year |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-XSS-Protection` | `1; mode=block` | Enable browser XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer information |
| `Permissions-Policy` | Various | Disable unnecessary browser features |

---

## Dependency Security

### Automated Scanning

**1. Dependabot (GitHub)**

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**2. Safety (CLI)**

```bash
pip install safety
safety check --json
```

**3. Bandit (SAST)**

```bash
pip install bandit
bandit -r web/ src/ -f json -o security-report.json
```

### Manual Audits

```bash
# List installed packages
pip list

# Check for outdated packages
pip list --outdated

# Audit with pip-audit
pip install pip-audit
pip-audit
```

### Dependency Pinning

```ini
# requirements.txt
fastapi==0.104.1  # Pinned version
uvicorn[standard]>=0.24.0,<1.0.0  # Range
```

---

## Incident Response

### Incident Response Plan

**1. Detection**
- Monitor logs for anomalies
- Health check failures
- User reports
- Security scanner alerts

**2. Containment**
- Disable affected endpoints
- Block malicious IPs
- Isolate compromised systems
- Preserve evidence

**3. Eradication**
- Identify root cause
- Remove malware/backdoors
- Patch vulnerabilities
- Reset credentials

**4. Recovery**
- Restore from backups
- Verify system integrity
- Gradual service restoration
- Monitor for reinfection

**5. Post-Incident**
- Document incident
- Update security measures
- Train team
- Notify affected parties (if required)

### Contact Information

**Security Team:**
- Email: security@yourdomain.com
- Phone: +XX XXX XXXX
- On-call: PagerDuty/Opsgenie

---

## Compliance

### GDPR (EU)

If processing EU user data:
- [ ] Data Processing Agreement
- [ ] Privacy Policy
- [ ] User consent mechanisms
- [ ] Right to erasure (data deletion)
- [ ] Data breach notification (72 hours)

### SOC 2

For enterprise customers:
- [ ] Access controls
- [ ] Encryption in transit and at rest
- [ ] Audit logging
- [ ] Regular security assessments
- [ ] Incident response procedures

---

## Security Resources

**Tools:**
- [OWASP ZAP](https://www.zaproxy.org/) - Web application security scanner
- [Nmap](https://nmap.org/) - Network security scanner
- [Bandit](https://bandit.readthedocs.io/) - Python SAST
- [Safety](https://pyup.io/safety/) - Dependency checker

**References:**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last Updated:** 2025-12-01  
**Version:** 2.0.0  
**Maintainer:** Security Team
