# AppImage Re-Signer - API Documentation

**Version:** 2.0.0  
**Base URL:** `http://localhost:8000`  
**Content-Type:** `application/json` (where applicable)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health & Status](#health--status)
3. [Session Management](#session-management)
4. [File Upload](#file-upload)
5. [Signing Operations](#signing-operations)
6. [Verification](#verification)
7. [Download](#download)
8. [Error Codes](#error-codes)
9. [Rate Limits](#rate-limits)
10. [Examples](#examples)

---

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing:
- API Keys
- OAuth 2.0
- JWT Tokens

---

## Health & Status

### GET `/health`

Check application health and system status.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "application": "AppImage Re-Signer",
  "version": "2.0.0",
  "timestamp": "2025-12-01T10:30:00.123456",
  "uptime_check": "ok",
  "gpg": {
    "available": true,
    "version": "2.4.0"
  },
  "sessions": {
    "active": 5,
    "cleanup_interval": "1 hour",
    "retention": "24 hours"
  },
  "scheduler": {
    "running": true
  }
}
```

**Use Cases:**
- Docker HEALTHCHECK
- Monitoring systems (Prometheus, Nagios)
- Load balancer health probes
- Deployment verification

---

## Session Management

### POST `/api/session/create`

Create a new signing session.

**Request Body:** None

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "expires_in_hours": 24
}
```

**Notes:**
- Session IDs are UUIDs
- Sessions expire after 24 hours (configurable via `CLEANUP_AFTER_HOURS`)
- Automatic cleanup runs every hour

---

### GET `/api/session/{session_id}/status`

Get current session status.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "signed",
  "error": null,
  "has_appimage": true,
  "has_key": true,
  "has_signed": true,
  "verification": {
    "valid": true,
    "key_id": "C407155E5D49FE6B",
    "fingerprint": "A1EA6539514E0105...",
    "username": "John Doe <john@example.com>",
    "trust_level": "TRUST_ULTIMATE",
    "timestamp": 1733051400
  }
}
```

**Status Values:**
- `initialized` - Session created
- `appimage_uploaded` - AppImage file uploaded
- `key_uploaded` - GPG key uploaded
- `signed` - Signing completed successfully
- `failed` - Signing failed (check `error` field)

---

### DELETE `/api/session/{session_id}`

Delete a session and clean up files.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`

```json
{
  "status": "deleted"
}
```

---

## File Upload

### POST `/api/upload/appimage`

Upload an AppImage file.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `session_id` (string, required) - Session UUID
- `file` (file, required) - AppImage file (.AppImage extension)

**Validation:**
- File extension must be `.AppImage`
- ELF header check (magic bytes: `7f 45 4c 46`)
- AppImage Type 2 format check (magic: `AI\x02` at offset 8)
- File size must be ≤ 500 MB (configurable via `MAX_FILE_SIZE_MB`)

**Response:** `200 OK`

```json
{
  "status": "success",
  "filename": "MyApp-1.0.0-x86_64.AppImage",
  "size": 104857600,
  "signature_info": {
    "has_signature": true,
    "type": "embedded",
    "size": 287,
    "signature_data": "-----BEGIN PGP SIGNATURE-----\n...",
    "metadata": {
      "raw_available": true,
      "key_id_short": "5D49FE6B",
      "signature_type": "binary",
      "creation_time": "2025-12-01 10:00:00"
    }
  }
}
```

**Signature Info:**
- `has_signature` - Boolean indicating signature presence
- `type` - "embedded" or "external" (.asc file)
- `size` - Signature size in bytes
- `signature_data` - PGP signature content (ASCII-armored)
- `metadata` - Optional metadata if available

**Error Responses:**

**400 Bad Request** - Invalid file

```json
{
  "detail": "File must be an AppImage"
}
```

**400 Bad Request** - Invalid AppImage

```json
{
  "detail": "Invalid AppImage: Not an ELF file (invalid magic bytes)"
}
```

**404 Not Found** - Invalid session

```json
{
  "detail": "Session not found"
}
```

---

### POST `/api/upload/key`

Upload a GPG private key file.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `session_id` (string, required) - Session UUID
- `file` (file, required) - GPG private key (.key, .gpg, or .asc)

**Response:** `200 OK`

```json
{
  "status": "success",
  "message": "Key uploaded successfully"
}
```

**Notes:**
- Key is imported into temporary GPG keyring
- Key file is deleted after signing
- Passphrase should be provided during signing

---

### POST `/api/upload/signature`

Upload an external .asc signature file for verification.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `session_id` (string, required) - Session UUID
- `file` (file, required) - Signature file (.asc)

**Response:** `200 OK`

```json
{
  "status": "success",
  "message": "Signature uploaded and verified",
  "verification": {
    "valid": true,
    "key_id": "C407155E5D49FE6B",
    "fingerprint": "A1EA6539514E0105C407155E5D49FE6B",
    "username": "John Doe <john@example.com>",
    "trust_level": "TRUST_ULTIMATE",
    "timestamp": 1733051400,
    "has_signature": true,
    "signature_type": "external"
  }
}
```

---

## Signing Operations

### POST `/api/sign`

Sign the uploaded AppImage.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `session_id` (string, required) - Session UUID
- `key_id` (string, optional) - GPG Key ID (if not uploading key file)
- `passphrase` (string, optional) - Key passphrase
- `embed_signature` (boolean, optional, default: false) - Embed signature in AppImage

**Request Example:**

```bash
curl -X POST http://localhost:8000/api/sign \
  -F "session_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "key_id=C407155E5D49FE6B" \
  -F "passphrase=my-secret-passphrase" \
  -F "embed_signature=true"
```

**Response:** `200 OK`

```json
{
  "status": "success",
  "message": "AppImage signed successfully",
  "verification": {
    "valid": true,
    "key_id": "C407155E5D49FE6B",
    "fingerprint": "A1EA6539514E0105C407155E5D49FE6B",
    "username": "John Doe <john@example.com>",
    "trust_level": "TRUST_ULTIMATE",
    "timestamp": 1733051400,
    "has_signature": true,
    "signature_type": "embedded"
  },
  "download_urls": {
    "appimage": "/api/download/appimage/550e8400-e29b-41d4-a716-446655440000",
    "signature": "/api/download/signature/550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Security Notes:**
- Passphrase is **never stored** in session or logs
- Passphrase is overwritten in memory after use
- Empty passphrases are rejected
- Key file is deleted after signing

**Error Responses:**

**400 Bad Request** - Empty passphrase

```json
{
  "detail": "Passphrase cannot be empty. If your key has no passphrase, omit the field."
}
```

**400 Bad Request** - No AppImage uploaded

```json
{
  "detail": "No AppImage uploaded"
}
```

**500 Internal Server Error** - Signing failed

```json
{
  "detail": "Signing error: gpg: signing failed: Bad passphrase"
}
```

---

## Verification

### POST `/api/verify/uploaded/{session_id}`

Verify signature of uploaded AppImage.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`

```json
{
  "status": "success",
  "verification": {
    "valid": true,
    "key_id": "C407155E5D49FE6B",
    "fingerprint": "A1EA6539514E0105C407155E5D49FE6B",
    "username": "John Doe <john@example.com>",
    "trust_level": "TRUST_ULTIMATE",
    "timestamp": 1733051400,
    "has_signature": true,
    "signature_type": "embedded"
  }
}
```

**Trust Levels:**
- `TRUST_UNDEFINED` - Trust not defined
- `TRUST_NEVER` - Never trust this key
- `TRUST_MARGINAL` - Marginally trusted
- `TRUST_FULLY` - Fully trusted
- `TRUST_ULTIMATE` - Ultimate trust (own key)

---

### GET `/api/verify/{session_id}`

Verify signature of signed AppImage.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** Same as `/api/verify/uploaded/{session_id}`

---

## Download

### GET `/api/download/appimage/{session_id}`

Download signed AppImage file.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`
- **Content-Type:** `application/octet-stream`
- **Content-Disposition:** `attachment; filename="MyApp-1.0.0-x86_64.AppImage"`

**Notes:**
- UUID prefix is removed from filename
- Original filename is preserved

---

### GET `/api/download/signature/{session_id}`

Download signature file (.asc).

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`
- **Content-Type:** `application/pgp-signature`
- **Content-Disposition:** `attachment; filename="MyApp-1.0.0-x86_64.AppImage.asc"`

---

### GET `/api/download/zip/{session_id}`

Download both signed AppImage and signature as ZIP archive.

**Path Parameters:**
- `session_id` (string, required) - Session UUID

**Response:** `200 OK`
- **Content-Type:** `application/zip`
- **Content-Disposition:** `attachment; filename="MyApp-1.0.0-x86_64_signed.zip"`

**ZIP Contents:**
- `MyApp-1.0.0-x86_64.AppImage` - Signed AppImage
- `MyApp-1.0.0-x86_64.AppImage.asc` - Signature file

**Notes:**
- Temporary ZIP file is created and cleaned up automatically
- Both files have UUID prefix removed
- Compression: `ZIP_DEFLATED`

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request parameters or validation failed |
| 404 | Not Found | Session or resource not found |
| 500 | Internal Server Error | Server-side error during processing |

### Application Error Codes

All errors return JSON with `detail` field:

```json
{
  "detail": "Error message here"
}
```

**Common Errors:**

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `Session not found` | Invalid or expired session ID | Create new session |
| `File must be an AppImage` | Wrong file extension | Upload .AppImage file |
| `Invalid AppImage: Not an ELF file` | Invalid file format | Upload valid AppImage |
| `No AppImage uploaded` | Signing without upload | Upload AppImage first |
| `Passphrase cannot be empty` | Empty passphrase provided | Omit passphrase field or provide valid one |
| `Signing failed` | GPG signing error | Check key ID, passphrase, or GPG logs |
| `Signed AppImage not found` | Downloading before signing | Complete signing first |

---

## Rate Limits

Currently, no rate limiting is implemented. For production:

**Recommended Limits:**
- `/api/upload/*`: 10 requests/minute per IP
- `/api/sign`: 5 requests/minute per IP
- `/api/download/*`: 50 requests/minute per IP

**Implementation:** Use `slowapi` library

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/sign")
@limiter.limit("5/minute")
async def sign_appimage(...):
    ...
```

---

## Examples

### Complete Workflow (curl)

```bash
# 1. Create session
SESSION_ID=$(curl -X POST http://localhost:8000/api/session/create | jq -r '.session_id')
echo "Session: $SESSION_ID"

# 2. Upload AppImage
curl -X POST http://localhost:8000/api/upload/appimage \
  -F "session_id=$SESSION_ID" \
  -F "file=@MyApp-1.0.0-x86_64.AppImage"

# 3. Upload GPG key (or use key_id)
curl -X POST http://localhost:8000/api/upload/key \
  -F "session_id=$SESSION_ID" \
  -F "file=@private.key"

# 4. Sign AppImage
curl -X POST http://localhost:8000/api/sign \
  -F "session_id=$SESSION_ID" \
  -F "passphrase=my-passphrase" \
  -F "embed_signature=true"

# 5. Download ZIP
curl -O -J http://localhost:8000/api/download/zip/$SESSION_ID

# 6. Verify signature
curl -X POST http://localhost:8000/api/verify/uploaded/$SESSION_ID

# 7. Cleanup (optional)
curl -X DELETE http://localhost:8000/api/session/$SESSION_ID
```

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create session
response = requests.post(f"{BASE_URL}/api/session/create")
session_id = response.json()["session_id"]
print(f"Session: {session_id}")

# 2. Upload AppImage
with open("MyApp-1.0.0-x86_64.AppImage", "rb") as f:
    files = {"file": f}
    data = {"session_id": session_id}
    response = requests.post(f"{BASE_URL}/api/upload/appimage", files=files, data=data)
    print("Upload:", response.json())

# 3. Sign with existing key
data = {
    "session_id": session_id,
    "key_id": "C407155E5D49FE6B",
    "passphrase": "my-passphrase",
    "embed_signature": "true"
}
response = requests.post(f"{BASE_URL}/api/sign", data=data)
print("Signing:", response.json())

# 4. Download ZIP
response = requests.get(f"{BASE_URL}/api/download/zip/{session_id}")
with open("signed.zip", "wb") as f:
    f.write(response.content)
print("Downloaded signed.zip")

# 5. Cleanup
requests.delete(f"{BASE_URL}/api/session/{session_id}")
```

### JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function signAppImage() {
  // 1. Create session
  const sessionRes = await axios.post(`${BASE_URL}/api/session/create`);
  const sessionId = sessionRes.data.session_id;
  console.log(`Session: ${sessionId}`);

  // 2. Upload AppImage
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('file', fs.createReadStream('MyApp-1.0.0-x86_64.AppImage'));
  
  await axios.post(`${BASE_URL}/api/upload/appimage`, formData, {
    headers: formData.getHeaders()
  });

  // 3. Sign
  const signData = new FormData();
  signData.append('session_id', sessionId);
  signData.append('key_id', 'C407155E5D49FE6B');
  signData.append('passphrase', 'my-passphrase');
  signData.append('embed_signature', 'true');
  
  const signRes = await axios.post(`${BASE_URL}/api/sign`, signData, {
    headers: signData.getHeaders()
  });
  console.log('Signed:', signRes.data);

  // 4. Download ZIP
  const zipRes = await axios.get(`${BASE_URL}/api/download/zip/${sessionId}`, {
    responseType: 'arraybuffer'
  });
  fs.writeFileSync('signed.zip', zipRes.data);
  console.log('Downloaded signed.zip');

  // 5. Cleanup
  await axios.delete(`${BASE_URL}/api/session/${sessionId}`);
}

signAppImage().catch(console.error);
```

---

## OpenAPI/Swagger Integration

To enable interactive API documentation, add FastAPI's built-in Swagger UI:

**Access:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

**Configuration in `web/app.py`:**

```python
app = FastAPI(
    title="AppImage Re-Signer",
    description="Web service for removing and adding GPG signatures to Linux AppImage files",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
```

**Custom OpenAPI Tags:**

```python
tags_metadata = [
    {"name": "health", "description": "Health check and status"},
    {"name": "sessions", "description": "Session management"},
    {"name": "upload", "description": "File upload operations"},
    {"name": "signing", "description": "Signing operations"},
    {"name": "verification", "description": "Signature verification"},
    {"name": "download", "description": "Download signed files"}
]

app = FastAPI(openapi_tags=tags_metadata)

@app.get("/health", tags=["health"])
async def health_check():
    ...
```

---

## WebSocket Support (Future)

For real-time progress updates, WebSocket support could be added:

**Endpoint:** `ws://localhost:8000/ws/progress/{session_id}`

**Messages:**

```json
{
  "type": "upload_progress",
  "percent": 45.5,
  "speed": 12.3,
  "eta": 15
}
```

```json
{
  "type": "signing_progress",
  "status": "generating_signature",
  "percent": 75
}
```

**Implementation:** Use `fastapi.WebSocket`

---

## Security Considerations

### HTTPS Only
In production, always use HTTPS:

```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app.add_middleware(HTTPSRedirectMiddleware)
```

### CORS
Configure CORS properly:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

### Content Security Policy
Add CSP headers:

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response
```

---

## Monitoring

### Prometheus Metrics

Example metrics endpoint:

```python
from prometheus_client import Counter, Histogram, generate_latest

signatures_total = Counter('appimage_signatures_total', 'Total signatures created')
signing_duration = Histogram('appimage_signing_duration_seconds', 'Signing duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Logging

All operations are logged to `logs/appimage-resigner.log`:

```
2025-12-01 10:30:15 | INFO     | web.app | create_session:180 | Session created | session_id=550e8400...
2025-12-01 10:30:20 | INFO     | web.app | upload_appimage:245 | AppImage uploaded | session_id=550e8400... | filename=MyApp.AppImage | size=104857600
2025-12-01 10:30:25 | INFO     | web.app | sign_appimage:420 | Signing completed | session_id=550e8400... | embed=true
```

---

## Support

**Issues:** https://github.com/xXRoxXeRXx/appimage-resigner/issues  
**Documentation:** https://github.com/xXRoxXeRXx/appimage-resigner/docs  
**Version:** 2.0.0  
**Last Updated:** 2025-12-01
