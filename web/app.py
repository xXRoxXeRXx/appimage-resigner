#!/usr/bin/env python3
"""
FastAPI Web Application for AppImage Re-Signing
Provides REST API endpoints for uploading, signing, and downloading AppImages
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiofiles

# Import our existing signing logic
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.resigner import AppImageResigner
from src.verify import AppImageVerifier
from src.key_manager import GPGKeyManager


# Configuration
UPLOAD_DIR = Path("uploads")
SIGNED_DIR = Path("signed")
TEMP_KEYS_DIR = Path("temp_keys")
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
CLEANUP_AFTER_HOURS = 24

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
SIGNED_DIR.mkdir(exist_ok=True)
TEMP_KEYS_DIR.mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(
    title="AppImage Re-Signer",
    description="Web service for removing and adding GPG signatures to Linux AppImage files",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


# Session storage (in production, use Redis or database)
sessions = {}


class SigningSession:
    """Represents a signing session with uploaded files"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.appimage_path: Optional[Path] = None
        self.key_path: Optional[Path] = None
        self.signed_path: Optional[Path] = None
        self.signature_path: Optional[Path] = None
        self.status = "initialized"
        self.error: Optional[str] = None
        self.verification_result: Optional[dict] = None


def cleanup_session(session_id: str):
    """Clean up session files"""
    if session_id in sessions:
        session = sessions[session_id]
        
        # Delete uploaded files
        if session.appimage_path and session.appimage_path.exists():
            session.appimage_path.unlink()
        if session.key_path and session.key_path.exists():
            session.key_path.unlink()
        if session.signed_path and session.signed_path.exists():
            session.signed_path.unlink()
        if session.signature_path and session.signature_path.exists():
            session.signature_path.unlink()
        
        # Remove from sessions
        del sessions[session_id]


def cleanup_old_sessions():
    """Clean up sessions older than CLEANUP_AFTER_HOURS"""
    cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
    
    old_sessions = [
        sid for sid, session in sessions.items()
        if session.created_at < cutoff_time
    ]
    
    for sid in old_sessions:
        cleanup_session(sid)


@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("web/static/index.html")


@app.post("/api/session/create")
async def create_session():
    """Create a new signing session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = SigningSession(session_id)
    
    return {
        "session_id": session_id,
        "status": "created",
        "expires_in_hours": CLEANUP_AFTER_HOURS
    }


@app.post("/api/upload/appimage")
async def upload_appimage(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload an AppImage file"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Validate file
    if not file.filename.endswith('.AppImage'):
        raise HTTPException(status_code=400, detail="File must be an AppImage")
    
    # Save file
    file_path = UPLOAD_DIR / f"{session_id}_{file.filename}"
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
            
            await out_file.write(content)
        
        session.appimage_path = file_path
        session.status = "appimage_uploaded"
        
        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        session.error = str(e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/upload/key")
async def upload_key(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a GPG private key file"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Save key file
    key_path = TEMP_KEYS_DIR / f"{session_id}_private.key"
    
    try:
        async with aiofiles.open(key_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        session.key_path = key_path
        session.status = "key_uploaded"
        
        return {
            "status": "success",
            "message": "Key uploaded successfully"
        }
        
    except Exception as e:
        session.error = str(e)
        raise HTTPException(status_code=500, detail=f"Key upload failed: {str(e)}")


@app.post("/api/sign")
async def sign_appimage(
    session_id: str = Form(...),
    key_id: Optional[str] = Form(None),
    passphrase: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """Sign the uploaded AppImage"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.appimage_path:
        raise HTTPException(status_code=400, detail="No AppImage uploaded")
    
    try:
        # Import key if uploaded
        if session.key_path:
            manager = GPGKeyManager()
            manager.import_key(str(session.key_path))
        
        # Initialize resigner
        resigner = AppImageResigner()
        
        # Sign the AppImage
        output_path = SIGNED_DIR / f"{session_id}_{session.appimage_path.name}"
        signature_path = Path(str(output_path) + ".asc")
        
        # Copy original to signed directory
        shutil.copy2(session.appimage_path, output_path)
        
        # Sign
        success = resigner.sign_appimage(
            str(output_path),
            key_id=key_id,
            passphrase=passphrase
        )
        
        if success:
            session.signed_path = output_path
            session.signature_path = signature_path
            session.status = "signed"
            
            # Verify signature
            verifier = AppImageVerifier()
            verification = verifier.verify_signature(str(output_path))
            session.verification_result = verification
            
            return {
                "status": "success",
                "message": "AppImage signed successfully",
                "verification": verification,
                "download_urls": {
                    "appimage": f"/api/download/appimage/{session_id}",
                    "signature": f"/api/download/signature/{session_id}"
                }
            }
        else:
            session.status = "failed"
            session.error = "Signing failed"
            raise HTTPException(status_code=500, detail="Signing failed")
            
    except Exception as e:
        session.status = "failed"
        session.error = str(e)
        raise HTTPException(status_code=500, detail=f"Signing error: {str(e)}")


@app.get("/api/verify/{session_id}")
async def verify_signature(session_id: str):
    """Verify the signature of a signed AppImage"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.signed_path:
        raise HTTPException(status_code=400, detail="No signed AppImage available")
    
    try:
        verifier = AppImageVerifier()
        result = verifier.verify_signature(str(session.signed_path))
        
        return {
            "status": "success",
            "verification": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")


@app.get("/api/download/appimage/{session_id}")
async def download_appimage(session_id: str, background_tasks: BackgroundTasks):
    """Download the signed AppImage"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.signed_path or not session.signed_path.exists():
        raise HTTPException(status_code=404, detail="Signed AppImage not found")
    
    # Schedule cleanup after download
    background_tasks.add_task(cleanup_session, session_id)
    
    return FileResponse(
        session.signed_path,
        media_type="application/octet-stream",
        filename=session.signed_path.name
    )


@app.get("/api/download/signature/{session_id}")
async def download_signature(session_id: str):
    """Download the signature file"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    if not session.signature_path or not session.signature_path.exists():
        raise HTTPException(status_code=404, detail="Signature file not found")
    
    return FileResponse(
        session.signature_path,
        media_type="application/pgp-signature",
        filename=session.signature_path.name
    )


@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get the current status of a session"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "session_id": session_id,
        "status": session.status,
        "error": session.error,
        "has_appimage": session.appimage_path is not None,
        "has_key": session.key_path is not None,
        "has_signed": session.signed_path is not None,
        "verification": session.verification_result
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and clean up files"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cleanup_session(session_id)
    
    return {"status": "deleted"}


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    # Clean up old sessions
    cleanup_old_sessions()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
