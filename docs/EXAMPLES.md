# AppImage Re-Signer - Examples & Usage Guide

**Version:** 2.0.0  
**Last Updated:** 2025-12-01

---

## Table of Contents

1. [Quick Start Examples](#quick-start-examples)
2. [CLI Usage](#cli-usage)
3. [API Examples](#api-examples)
4. [Python Scripts](#python-scripts)
5. [JavaScript/Node.js Integration](#javascriptnodejs-integration)
6. [Batch Processing](#batch-processing)
7. [CI/CD Integration](#cicd-integration)
8. [Docker Compose Examples](#docker-compose-examples)
9. [Advanced Workflows](#advanced-workflows)
10. [Troubleshooting Scenarios](#troubleshooting-scenarios)

---

## Quick Start Examples

### Example 1: Sign an AppImage (Web Interface)

1. **Start the server:**
```bash
cd appimage-resigner
python -m uvicorn web.app:app --reload --port 8000
```

2. **Open browser:** `http://localhost:8000`

3. **Upload AppImage:** Drag & drop or click to browse

4. **Upload GPG Key:** Upload your private key file

5. **Enter Passphrase:** Type your GPG key passphrase

6. **Sign:** Click "Sign AppImage" button

7. **Download:** Download signed AppImage and signature

### Example 2: Verify Signature (CLI)

```bash
# Verify with GPG
gpg --verify Nextcloud-4.0.2-x86_64.AppImage.asc Nextcloud-4.0.2-x86_64.AppImage

# Or use our script
python check_signature.py signed/Nextcloud-4.0.2-x86_64.AppImage
```

### Example 3: Embed Signature (CLI)

```bash
python embed_signature.py \
    signed/Nextcloud-4.0.2-x86_64.AppImage \
    signed/Nextcloud-4.0.2-x86_64.AppImage.asc \
    -o signed/Nextcloud-4.0.2-x86_64-embedded.AppImage
```

---

## CLI Usage

### Basic Commands

#### 1. Sign AppImage

```bash
# Basic signing
gpg --detach-sign --armor --output app.AppImage.asc app.AppImage

# Sign with specific key
gpg --default-key YOUR_KEY_ID --detach-sign --armor app.AppImage

# Sign with custom output
gpg -u YOUR_KEY_ID --detach-sign --armor -o custom-signature.asc app.AppImage
```

#### 2. Verify Signature

```bash
# Verify detached signature
gpg --verify app.AppImage.asc app.AppImage

# Verify with public key import
gpg --import public-key.asc
gpg --verify app.AppImage.asc app.AppImage

# Show signature details
gpg --verify --verbose app.AppImage.asc app.AppImage
```

#### 3. Embed Signature

```bash
# Embed signature into AppImage
python embed_signature.py app.AppImage app.AppImage.asc -o app-signed.AppImage

# With verbose output
python embed_signature.py app.AppImage app.AppImage.asc -o app-signed.AppImage -v

# Overwrite original (dangerous!)
python embed_signature.py app.AppImage app.AppImage.asc -o app.AppImage --force
```

#### 4. Check Embedded Signature

```bash
# Check if AppImage has embedded signature
python check_signature.py app.AppImage

# Verbose output
python check_signature.py app.AppImage -v

# Export embedded signature
python analyze_signatures.py app.AppImage --export signature.asc
```

### Key Management

#### Import Keys

```bash
# Import public key
gpg --import public-key.asc

# Import private key
gpg --import private-key.asc

# Import from keyserver
gpg --keyserver keys.openpgp.org --recv-keys KEY_ID
```

#### List Keys

```bash
# List public keys
gpg --list-keys

# List private keys
gpg --list-secret-keys

# Show key details
gpg --list-keys --keyid-format LONG
```

#### Export Keys

```bash
# Export public key
gpg --armor --export YOUR_EMAIL > public-key.asc

# Export private key
gpg --armor --export-secret-keys YOUR_EMAIL > private-key.asc

# Export specific key by ID
gpg --armor --export KEY_ID > public-key.asc
```

---

## API Examples

### Example 1: Complete Workflow (curl)

```bash
#!/bin/bash
set -e

# 1. Create session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/session/create)
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Created session: $SESSION_ID"

# 2. Upload AppImage
curl -X POST \
    "http://localhost:8000/api/upload/appimage?session_id=$SESSION_ID" \
    -F "file=@Nextcloud-4.0.2-x86_64.AppImage"
echo "AppImage uploaded"

# 3. Upload GPG key
curl -X POST \
    "http://localhost:8000/api/upload/key?session_id=$SESSION_ID" \
    -F "file=@my-private-key.asc"
echo "GPG key uploaded"

# 4. Sign AppImage
SIGN_RESPONSE=$(curl -s -X POST \
    "http://localhost:8000/api/sign?session_id=$SESSION_ID" \
    -H "Content-Type: application/json" \
    -d '{"passphrase": "my-secure-passphrase"}')
echo "Signing result: $SIGN_RESPONSE"

# 5. Download signed AppImage
curl -X GET \
    "http://localhost:8000/api/download/appimage?session_id=$SESSION_ID" \
    -o "Nextcloud-4.0.2-x86_64-signed.AppImage"
echo "Downloaded signed AppImage"

# 6. Download signature
curl -X GET \
    "http://localhost:8000/api/download/signature?session_id=$SESSION_ID" \
    -o "Nextcloud-4.0.2-x86_64-signed.AppImage.asc"
echo "Downloaded signature"

# 7. Download ZIP (both files)
curl -X GET \
    "http://localhost:8000/api/download/zip?session_id=$SESSION_ID" \
    -o "Nextcloud-4.0.2-x86_64-signed.zip"
echo "Downloaded ZIP archive"

# 8. Verify signature
gpg --verify Nextcloud-4.0.2-x86_64-signed.AppImage.asc Nextcloud-4.0.2-x86_64-signed.AppImage

# 9. Cleanup session
curl -X DELETE "http://localhost:8000/api/session/$SESSION_ID"
echo "Session deleted"
```

### Example 2: Upload with Progress (curl)

```bash
# Upload with progress bar
curl -X POST \
    "http://localhost:8000/api/upload/appimage?session_id=$SESSION_ID" \
    -F "file=@large-app.AppImage" \
    --progress-bar \
    -o /dev/null

# Upload with detailed progress
curl -X POST \
    "http://localhost:8000/api/upload/appimage?session_id=$SESSION_ID" \
    -F "file=@large-app.AppImage" \
    --progress-bar | tee upload-progress.log
```

### Example 3: Health Check

```bash
# Check server health
curl -s http://localhost:8000/health | jq

# Expected output:
# {
#   "status": "ok",
#   "version": "2.0.0",
#   "gpg_available": true,
#   "timestamp": "2025-12-01T10:30:00"
# }
```

### Example 4: Session Status

```bash
# Check session status
curl -s "http://localhost:8000/api/session/$SESSION_ID" | jq

# Expected output:
# {
#   "session_id": "550e8400-e29b-41d4-a716-446655440000",
#   "appimage_uploaded": true,
#   "key_uploaded": true,
#   "signed": false,
#   "created_at": "2025-12-01T10:30:00"
# }
```

---

## Python Scripts

### Example 1: Complete Signing Workflow

```python
#!/usr/bin/env python3
"""
Complete AppImage signing workflow using the API
"""
import requests
import json
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
APPIMAGE_PATH = Path("Nextcloud-4.0.2-x86_64.AppImage")
KEY_PATH = Path("my-private-key.asc")
PASSPHRASE = "my-secure-passphrase"
OUTPUT_DIR = Path("output")

def main():
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 1. Create session
    print("Creating session...")
    response = requests.post(f"{API_BASE}/api/session/create")
    response.raise_for_status()
    session_id = response.json()["session_id"]
    print(f"✓ Session created: {session_id}")
    
    # 2. Upload AppImage
    print("Uploading AppImage...")
    with open(APPIMAGE_PATH, 'rb') as f:
        files = {'file': (APPIMAGE_PATH.name, f, 'application/octet-stream')}
        response = requests.post(
            f"{API_BASE}/api/upload/appimage",
            params={"session_id": session_id},
            files=files
        )
    response.raise_for_status()
    print(f"✓ AppImage uploaded")
    
    # 3. Upload GPG key
    print("Uploading GPG key...")
    with open(KEY_PATH, 'rb') as f:
        files = {'file': (KEY_PATH.name, f, 'application/pgp-keys')}
        response = requests.post(
            f"{API_BASE}/api/upload/key",
            params={"session_id": session_id},
            files=files
        )
    response.raise_for_status()
    print(f"✓ GPG key uploaded")
    
    # 4. Sign AppImage
    print("Signing AppImage...")
    response = requests.post(
        f"{API_BASE}/api/sign",
        params={"session_id": session_id},
        json={"passphrase": PASSPHRASE}
    )
    response.raise_for_status()
    result = response.json()
    print(f"✓ Signed: {result['message']}")
    
    # 5. Download signed AppImage
    print("Downloading signed AppImage...")
    response = requests.get(
        f"{API_BASE}/api/download/appimage",
        params={"session_id": session_id}
    )
    response.raise_for_status()
    
    output_appimage = OUTPUT_DIR / APPIMAGE_PATH.name
    with open(output_appimage, 'wb') as f:
        f.write(response.content)
    print(f"✓ Downloaded: {output_appimage}")
    
    # 6. Download signature
    print("Downloading signature...")
    response = requests.get(
        f"{API_BASE}/api/download/signature",
        params={"session_id": session_id}
    )
    response.raise_for_status()
    
    output_signature = OUTPUT_DIR / f"{APPIMAGE_PATH.name}.asc"
    with open(output_signature, 'wb') as f:
        f.write(response.content)
    print(f"✓ Downloaded: {output_signature}")
    
    # 7. Verify signature locally
    print("Verifying signature...")
    import subprocess
    result = subprocess.run(
        ["gpg", "--verify", str(output_signature), str(output_appimage)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✓ Signature valid!")
    else:
        print(f"✗ Signature invalid: {result.stderr}")
    
    # 8. Cleanup session
    print("Cleaning up...")
    response = requests.delete(f"{API_BASE}/api/session/{session_id}")
    response.raise_for_status()
    print("✓ Session deleted")
    
    print("\n✅ Complete! Files saved to:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
```

### Example 2: Batch Signing

```python
#!/usr/bin/env python3
"""
Batch sign multiple AppImages
"""
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "http://localhost:8000"
KEY_PATH = Path("my-private-key.asc")
PASSPHRASE = "my-secure-passphrase"
APPIMAGE_DIR = Path("appimages")
OUTPUT_DIR = Path("signed")

def sign_appimage(appimage_path: Path) -> dict:
    """Sign a single AppImage"""
    try:
        # Create session
        response = requests.post(f"{API_BASE}/api/session/create")
        session_id = response.json()["session_id"]
        
        # Upload AppImage
        with open(appimage_path, 'rb') as f:
            requests.post(
                f"{API_BASE}/api/upload/appimage",
                params={"session_id": session_id},
                files={'file': f}
            ).raise_for_status()
        
        # Upload key
        with open(KEY_PATH, 'rb') as f:
            requests.post(
                f"{API_BASE}/api/upload/key",
                params={"session_id": session_id},
                files={'file': f}
            ).raise_for_status()
        
        # Sign
        requests.post(
            f"{API_BASE}/api/sign",
            params={"session_id": session_id},
            json={"passphrase": PASSPHRASE}
        ).raise_for_status()
        
        # Download ZIP
        response = requests.get(
            f"{API_BASE}/api/download/zip",
            params={"session_id": session_id}
        )
        
        output_zip = OUTPUT_DIR / f"{appimage_path.stem}-signed.zip"
        with open(output_zip, 'wb') as f:
            f.write(response.content)
        
        # Cleanup
        requests.delete(f"{API_BASE}/api/session/{session_id}")
        
        return {
            "file": appimage_path.name,
            "status": "success",
            "output": output_zip
        }
    
    except Exception as e:
        return {
            "file": appimage_path.name,
            "status": "error",
            "error": str(e)
        }

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Find all AppImages
    appimages = list(APPIMAGE_DIR.glob("*.AppImage"))
    print(f"Found {len(appimages)} AppImages to sign")
    
    # Sign in parallel (max 4 concurrent)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(sign_appimage, appimage): appimage
            for appimage in appimages
        }
        
        for future in as_completed(futures):
            result = future.result()
            if result["status"] == "success":
                print(f"✓ {result['file']} → {result['output']}")
            else:
                print(f"✗ {result['file']}: {result['error']}")

if __name__ == "__main__":
    main()
```

### Example 3: Signature Verification

```python
#!/usr/bin/env python3
"""
Verify AppImage signatures
"""
import subprocess
from pathlib import Path
from typing import Tuple

def verify_signature(appimage: Path, signature: Path) -> Tuple[bool, str]:
    """Verify an AppImage signature"""
    result = subprocess.run(
        ["gpg", "--verify", str(signature), str(appimage)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        # Extract signer info from stderr
        lines = result.stderr.split('\n')
        signer = next((l for l in lines if "Good signature" in l), "Unknown")
        return True, signer
    else:
        return False, result.stderr

def main():
    signed_dir = Path("signed")
    
    for appimage in signed_dir.glob("*.AppImage"):
        signature = appimage.with_suffix(appimage.suffix + '.asc')
        
        if not signature.exists():
            print(f"⚠️  {appimage.name}: No signature found")
            continue
        
        valid, info = verify_signature(appimage, signature)
        
        if valid:
            print(f"✓ {appimage.name}: Valid signature")
            print(f"  Signer: {info}")
        else:
            print(f"✗ {appimage.name}: Invalid signature")
            print(f"  Error: {info}")

if __name__ == "__main__":
    main()
```

---

## JavaScript/Node.js Integration

### Example 1: Chunked Upload (Browser)

```javascript
// Using the ChunkedUploader class
const uploader = new ChunkedUploader({
    chunkSize: 5 * 1024 * 1024,  // 5MB chunks
    maxRetries: 3,
    parallelUploads: 3,
    onProgress: (progress) => {
        console.log(`Progress: ${progress.progress.toFixed(1)}%`);
        console.log(`Speed: ${uploader.formatSpeed(progress.speed)}`);
        console.log(`ETA: ${uploader.formatETA(progress.eta)}`);
        
        // Update UI
        document.getElementById('progress-bar').style.width = `${progress.progress}%`;
        document.getElementById('progress-text').textContent = 
            `${progress.uploadedChunks}/${progress.totalChunks} chunks`;
    },
    onComplete: (result) => {
        console.log('Upload complete!', result);
        alert(`File uploaded: ${result.filename}`);
    },
    onError: (error) => {
        console.error('Upload failed:', error);
        alert(`Error: ${error.message}`);
    }
});

// Upload large AppImage
const fileInput = document.getElementById('file-input');
const sessionId = 'your-session-id'; // Get from session create

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    
    if (file.size > 50 * 1024 * 1024) {
        // Use chunked upload for files > 50MB
        await uploader.uploadFile(file, sessionId, 'appimage');
    } else {
        // Use regular upload for small files
        await regularUpload(file, sessionId);
    }
});
```

### Example 2: Sign AppImage (Node.js)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

const API_BASE = 'http://localhost:8000';

async function signAppImage(appImagePath, keyPath, passphrase) {
    try {
        // 1. Create session
        const sessionResponse = await axios.post(`${API_BASE}/api/session/create`);
        const sessionId = sessionResponse.data.session_id;
        console.log(`✓ Session created: ${sessionId}`);
        
        // 2. Upload AppImage
        const appImageForm = new FormData();
        appImageForm.append('file', fs.createReadStream(appImagePath));
        
        await axios.post(`${API_BASE}/api/upload/appimage?session_id=${sessionId}`, appImageForm, {
            headers: appImageForm.getHeaders()
        });
        console.log('✓ AppImage uploaded');
        
        // 3. Upload key
        const keyForm = new FormData();
        keyForm.append('file', fs.createReadStream(keyPath));
        
        await axios.post(`${API_BASE}/api/upload/key?session_id=${sessionId}`, keyForm, {
            headers: keyForm.getHeaders()
        });
        console.log('✓ GPG key uploaded');
        
        // 4. Sign
        await axios.post(`${API_BASE}/api/sign?session_id=${sessionId}`, {
            passphrase: passphrase
        });
        console.log('✓ Signed');
        
        // 5. Download ZIP
        const zipResponse = await axios.get(`${API_BASE}/api/download/zip?session_id=${sessionId}`, {
            responseType: 'arraybuffer'
        });
        
        const outputPath = path.join('output', `${path.basename(appImagePath, '.AppImage')}-signed.zip`);
        fs.writeFileSync(outputPath, zipResponse.data);
        console.log(`✓ Downloaded: ${outputPath}`);
        
        // 6. Cleanup
        await axios.delete(`${API_BASE}/api/session/${sessionId}`);
        console.log('✓ Session deleted');
        
        return outputPath;
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
        throw error;
    }
}

// Usage
signAppImage(
    'Nextcloud-4.0.2-x86_64.AppImage',
    'my-private-key.asc',
    'my-secure-passphrase'
).then(output => {
    console.log(`\n✅ Complete! Output: ${output}`);
}).catch(err => {
    console.error('Failed:', err);
    process.exit(1);
});
```

### Example 3: Chunked Upload (Node.js)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const crypto = require('crypto');

async function uploadLargeFile(filePath, sessionId, fileType = 'appimage') {
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
    const fileStats = fs.statSync(filePath);
    const totalSize = fileStats.size;
    const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);
    
    console.log(`File size: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
    console.log(`Total chunks: ${totalChunks}`);
    
    // 1. Initialize upload
    const initForm = new FormData();
    initForm.append('session_id', sessionId);
    initForm.append('filename', path.basename(filePath));
    initForm.append('total_size', totalSize);
    initForm.append('file_type', fileType);
    
    const initResponse = await axios.post(
        `${API_BASE}/api/upload/init`,
        initForm,
        { headers: initForm.getHeaders() }
    );
    
    console.log(`✓ Upload initialized`);
    
    // 2. Upload chunks
    const fileStream = fs.createReadStream(filePath, { highWaterMark: CHUNK_SIZE });
    let chunkNumber = 0;
    
    for await (const chunk of fileStream) {
        // Calculate checksum
        const checksum = crypto.createHash('md5').update(chunk).digest('hex');
        
        // Upload chunk
        const chunkForm = new FormData();
        chunkForm.append('chunk_number', chunkNumber);
        chunkForm.append('checksum', checksum);
        chunkForm.append('chunk', chunk);
        
        const chunkResponse = await axios.post(
            `${API_BASE}/api/upload/chunk/${sessionId}`,
            chunkForm,
            { headers: chunkForm.getHeaders() }
        );
        
        console.log(`✓ Chunk ${chunkNumber + 1}/${totalChunks} (${chunkResponse.data.progress.toFixed(1)}%)`);
        chunkNumber++;
    }
    
    // 3. Complete upload
    const completeForm = new FormData();
    completeForm.append('file_type', fileType);
    
    const completeResponse = await axios.post(
        `${API_BASE}/api/upload/complete/${sessionId}`,
        completeForm,
        { headers: completeForm.getHeaders() }
    );
    
    console.log(`✓ Upload complete: ${completeResponse.data.filename}`);
    return completeResponse.data;
}

// Usage
(async () => {
    const sessionResponse = await axios.post(`${API_BASE}/api/session/create`);
    const sessionId = sessionResponse.data.session_id;
    
    await uploadLargeFile('large-app.AppImage', sessionId, 'appimage');
    console.log('✅ Done!');
})();
```

### Example 4: React Component

```jsx
import React, { useState } from 'react';
import axios from 'axios';

const AppImageSigner = () => {
    const [sessionId, setSessionId] = useState(null);
    const [appImage, setAppImage] = useState(null);
    const [key, setKey] = useState(null);
    const [passphrase, setPassphrase] = useState('');
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('');

    const createSession = async () => {
        const response = await axios.post('/api/session/create');
        setSessionId(response.data.session_id);
        setStatus('Session created');
    };

    const uploadAppImage = async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        
        await axios.post(`/api/upload/appimage?session_id=${sessionId}`, formData, {
            onUploadProgress: (progressEvent) => {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                setProgress(percent);
            }
        });
        
        setAppImage(file.name);
        setStatus('AppImage uploaded');
    };

    const signAndDownload = async () => {
        // Sign
        await axios.post(`/api/sign?session_id=${sessionId}`, {
            passphrase: passphrase
        });
        setStatus('Signed successfully');
        
        // Download ZIP
        const response = await axios.get(`/api/download/zip?session_id=${sessionId}`, {
            responseType: 'blob'
        });
        
        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${appImage.replace('.AppImage', '')}-signed.zip`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        
        setStatus('Downloaded');
    };

    return (
        <div className="appimage-signer">
            <h2>AppImage Signer</h2>
            
            <button onClick={createSession}>Create Session</button>
            
            {sessionId && (
                <>
                    <input 
                        type="file" 
                        accept=".AppImage"
                        onChange={(e) => uploadAppImage(e.target.files[0])}
                    />
                    
                    {progress > 0 && <div>Upload Progress: {progress}%</div>}
                    
                    <input 
                        type="file" 
                        accept=".asc"
                        onChange={(e) => setKey(e.target.files[0])}
                    />
                    
                    <input 
                        type="password" 
                        placeholder="Passphrase"
                        value={passphrase}
                        onChange={(e) => setPassphrase(e.target.value)}
                    />
                    
                    <button onClick={signAndDownload}>Sign & Download</button>
                </>
            )}
            
            <div className="status">{status}</div>
        </div>
    );
};

export default AppImageSigner;
```

---

## Batch Processing

### Bash Script: Sign All AppImages

```bash
#!/bin/bash
# Sign all AppImages in a directory

APPIMAGE_DIR="./appimages"
KEY_PATH="./my-private-key.asc"
PASSPHRASE="my-secure-passphrase"
OUTPUT_DIR="./signed"

mkdir -p "$OUTPUT_DIR"

for appimage in "$APPIMAGE_DIR"/*.AppImage; do
    echo "Processing: $(basename "$appimage")"
    
    # Sign with GPG directly
    gpg --passphrase "$PASSPHRASE" \
        --batch --yes \
        --detach-sign --armor \
        --output "$OUTPUT_DIR/$(basename "$appimage").asc" \
        "$appimage"
    
    # Copy AppImage
    cp "$appimage" "$OUTPUT_DIR/"
    
    echo "✓ Signed: $(basename "$appimage")"
done

echo "✅ All AppImages signed! Output: $OUTPUT_DIR"
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Sign AppImage

on:
  release:
    types: [created]

jobs:
  sign:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Import GPG key
        env:
          GPG_PRIVATE_KEY: ${{ secrets.GPG_PRIVATE_KEY }}
        run: |
          echo "$GPG_PRIVATE_KEY" | gpg --import
      
      - name: Sign AppImage
        env:
          PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
        run: |
          gpg --passphrase "$PASSPHRASE" \
              --batch --yes \
              --detach-sign --armor \
              --output MyApp.AppImage.asc \
              MyApp.AppImage
      
      - name: Upload Release Assets
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./MyApp.AppImage.asc
          asset_name: MyApp.AppImage.asc
          asset_content_type: application/pgp-signature
```

### GitLab CI Example

```yaml
sign-appimage:
  stage: sign
  image: ubuntu:22.04
  
  before_script:
    - apt-get update && apt-get install -y gnupg
    - echo "$GPG_PRIVATE_KEY" | gpg --import
  
  script:
    - gpg --passphrase "$GPG_PASSPHRASE" --batch --yes --detach-sign --armor MyApp.AppImage
  
  artifacts:
    paths:
      - MyApp.AppImage.asc
  
  only:
    - tags
```

---

## Docker Compose Examples

### Example: Complete Stack

```yaml
version: '3.8'

services:
  appimage-resigner:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - MAX_FILE_SIZE_MB=500
      - SESSION_CLEANUP_HOURS=24
    volumes:
      - ./uploads:/app/uploads
      - ./signed:/app/signed
      - ./temp_keys:/app/temp_keys
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - appimage-resigner
    restart: unless-stopped
```

---

## Advanced Workflows

### Workflow 1: Automated Release Pipeline

```bash
#!/bin/bash
# Complete release pipeline

VERSION="1.0.0"
APPIMAGE="MyApp-${VERSION}-x86_64.AppImage"

# 1. Build AppImage
./build-appimage.sh

# 2. Sign AppImage
gpg --detach-sign --armor "$APPIMAGE"

# 3. Verify signature
gpg --verify "${APPIMAGE}.asc" "$APPIMAGE"

# 4. Create checksums
sha256sum "$APPIMAGE" > "${APPIMAGE}.sha256"

# 5. Upload to GitHub Release
gh release create "v${VERSION}" \
    "$APPIMAGE" \
    "${APPIMAGE}.asc" \
    "${APPIMAGE}.sha256" \
    --title "Release v${VERSION}" \
    --notes "See CHANGELOG.md"
```

### Workflow 2: Multi-Key Signing

```bash
#!/bin/bash
# Sign with multiple keys

APPIMAGE="MyApp.AppImage"
KEYS=("KEY_ID_1" "KEY_ID_2" "KEY_ID_3")

for key_id in "${KEYS[@]}"; do
    gpg --default-key "$key_id" \
        --detach-sign --armor \
        --output "${APPIMAGE}.${key_id}.asc" \
        "$APPIMAGE"
    
    echo "✓ Signed with key: $key_id"
done
```

---

## Troubleshooting Scenarios

### Scenario 1: "Invalid ELF Header"

**Problem:** Upload fails with "Not an ELF file"

**Solution:**
```bash
# Check file type
file MyApp.AppImage
# Should show: ELF 64-bit LSB executable

# Check magic bytes
xxd -l 4 MyApp.AppImage
# Should show: 7f 45 4c 46
```

### Scenario 2: "AppImage Type 2 Not Found"

**Problem:** AppImage doesn't have Type 2 magic

**Solution:**
```bash
# Check offset 8
xxd -s 8 -l 3 MyApp.AppImage
# Should show: 41 49 02 (AI\x02)

# If Type 1, convert to Type 2
appimagetool --appimage-extract-and-run MyApp.AppImage MyApp-Type2.AppImage
```

### Scenario 3: "GPG Signing Failed"

**Problem:** Signature creation fails

**Solutions:**
```bash
# 1. Check GPG installation
gpg --version

# 2. Check key exists
gpg --list-secret-keys

# 3. Test signing manually
echo "test" | gpg --clearsign

# 4. Check passphrase
gpg --export-secret-keys --armor > test.key
gpg --import test.key
# Enter passphrase to verify it works
```

### Scenario 4: "Session Not Found"

**Problem:** API returns 404 for session

**Solutions:**
```bash
# 1. Check session exists
curl -s http://localhost:8000/api/session/$SESSION_ID | jq

# 2. Check session timeout (default 24h)
# Sessions are auto-deleted after timeout

# 3. Create new session
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/session/create | jq -r '.session_id')
```

### Scenario 5: "File Too Large"

**Problem:** Upload rejected due to size limit

**Solutions:**
```bash
# 1. Check file size
du -h MyApp.AppImage

# 2. Increase limit in .env
echo "MAX_FILE_SIZE_MB=1000" >> .env

# 3. Restart server
docker-compose restart
```

---

**More Examples:** Check `/examples` directory in the repository  
**Questions?** Open an issue on GitHub  
**Support:** See [SUPPORT.md](SUPPORT.md)
