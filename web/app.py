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

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import our existing signing logic
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.resigner import AppImageResigner
from src.verify import AppImageVerifier
from src.key_manager import GPGKeyManager

# Import logging configuration
from web.core.logging_config import (
    setup_logging,
    get_logger,
    log_operation,
    log_audit_event,
    log_security_event,
    log_file_operation
)
from web.core.config import settings
from web.core.validation import validate_appimage_file
from web.core.security import get_client_ip, sanitize_filename
from web.services.streaming import StreamingUpload

# Import security middlewares
from web.middleware.security import (
    SecurityHeadersMiddleware,
    CSRFProtectionMiddleware,
    FileSizeValidationMiddleware,
    RateLimitMiddleware,
)

# Setup logging
setup_logging(
    log_level=settings.log_level,
    log_to_file=settings.log_to_file,
    log_to_console=settings.log_to_console
)
logger = get_logger(__name__)


# Configuration
UPLOAD_DIR = settings.upload_dir
SIGNED_DIR = settings.signed_dir
TEMP_KEYS_DIR = settings.temp_keys_dir
MAX_FILE_SIZE = settings.max_file_size_bytes
CLEANUP_AFTER_HOURS = settings.cleanup_after_hours

# Create directories
settings.create_directories()

# FastAPI app
app = FastAPI(
    title="AppImage Re-Signer",
    description="Web service for removing and adding GPG signatures to Linux AppImage files",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middlewares
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=True,
    hsts_max_age=31536000,  # 1 year
    enable_csp=True,
    csp_report_only=False,  # Set to True for testing, False for enforcement
)

app.add_middleware(
    FileSizeValidationMiddleware,
    max_size=settings.max_file_size_bytes
)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 100 requests per window
    window_seconds=60,  # 60 second window
)

# CSRF Protection (optional - currently in warning mode)
# app.add_middleware(
#     CSRFProtectionMiddleware,
#     token_header="X-CSRF-Token"
# )

logger.info("Security middlewares initialized")

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
        self.key_fingerprint: Optional[str] = None  # Store imported key fingerprint
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
        files_deleted = 0
        if session.appimage_path and session.appimage_path.exists():
            session.appimage_path.unlink()
            files_deleted += 1
        if session.key_path and session.key_path.exists():
            session.key_path.unlink()
            files_deleted += 1
        if session.signed_path and session.signed_path.exists():
            session.signed_path.unlink()
            files_deleted += 1
        if session.signature_path and session.signature_path.exists():
            session.signature_path.unlink()
            files_deleted += 1

        # Remove from sessions
        del sessions[session_id]
        logger.info(f"Session cleaned up | session_id={session_id} | files_deleted={files_deleted}")


def cleanup_old_sessions():
    """Clean up sessions older than CLEANUP_AFTER_HOURS"""
    cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)

    old_sessions = [
        sid for sid, session in sessions.items()
        if session.created_at < cutoff_time
    ]

    if old_sessions:
        logger.info(f"Cleaning up {len(old_sessions)} old sessions")

    for sid in old_sessions:
        cleanup_session(sid)

    return len(old_sessions)


# Setup background scheduler for automatic cleanup
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=cleanup_old_sessions,
    trigger=IntervalTrigger(hours=1),  # Run every hour
    id='cleanup_old_sessions',
    name='Clean up old sessions',
    replace_existing=True
)


@app.on_event("startup")
async def startup_event():
    """Start the background scheduler when the app starts"""
    scheduler.start()
    logger.info("Background scheduler started - sessions will be cleaned up every hour")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the background scheduler when the app shuts down"""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")


@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("web/static/index.html")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and Docker HEALTHCHECK.
    Returns application status, version, and GPG availability.
    """
    from datetime import datetime

    # Check GPG availability
    gpg_available = False
    gpg_version = None
    try:
        import gnupg
        gpg = gnupg.GPG()
        gpg_version = gpg.version
        gpg_available = gpg_version is not None
    except Exception as e:
        logger.warning(f"GPG check failed | error={str(e)}")

    # Get session count
    active_sessions = len(sessions)

    # Scheduler status
    scheduler_running = scheduler.running if scheduler else False

    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.version,
        "timestamp": datetime.now().isoformat(),
        "uptime_check": "ok",
        "gpg": {
            "available": gpg_available,
            "version": gpg_version
        },
        "sessions": {
            "active": active_sessions,
            "cleanup_interval": "1 hour",
            "retention": f"{CLEANUP_AFTER_HOURS} hours"
        },
        "scheduler": {
            "running": scheduler_running
        }
    }


@app.post("/api/session/create")
async def create_session():
    """Create a new signing session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = SigningSession(session_id)

    logger.info(f"Session created | session_id={session_id}")

    return {
        "session_id": session_id,
        "status": "created",
        "expires_in_hours": CLEANUP_AFTER_HOURS
    }


@app.post("/api/upload/appimage")
async def upload_appimage(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload an AppImage file"""

    # Get client info for audit logging
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    if session_id not in sessions:
        logger.warning(f"Upload attempt with invalid session | session_id={session_id}")
        log_security_event(
            logger,
            "invalid_session_upload",
            severity="warning",
            ip_address=client_ip,
            details={"session_id": session_id}
        )
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Sanitize filename
    original_filename = file.filename
    safe_filename = sanitize_filename(original_filename)

    # Validate file extension first
    if not safe_filename.endswith('.AppImage'):
        logger.warning(f"Invalid file upload | session_id={session_id} | filename={safe_filename}")
        log_audit_event(
            logger,
            "upload_rejected",
            session_id=session_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"reason": "invalid_extension", "filename": safe_filename}
        )
        raise HTTPException(status_code=400, detail="File must be an AppImage")

    # Save file temporarily
    file_path = UPLOAD_DIR / f"{session_id}_{safe_filename}"

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # Validate AppImage file (ELF header, size, format)
        is_valid, error_msg = validate_appimage_file(
            file_path,
            max_size_bytes=MAX_FILE_SIZE,
            check_elf=True,
            check_appimage=True
        )

        if not is_valid:
            # Delete invalid file
            file_path.unlink(missing_ok=True)
            logger.warning(f"Invalid AppImage file | session_id={session_id} | error={error_msg}")
            log_audit_event(
                logger,
                "upload_rejected",
                session_id=session_id,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"reason": "validation_failed", "error": error_msg, "filename": safe_filename}
            )
            raise HTTPException(status_code=400, detail=f"Invalid AppImage: {error_msg}")

        session.appimage_path = file_path
        session.status = "appimage_uploaded"

        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"AppImage uploaded | session_id={session_id} | filename={safe_filename} | size={file_size_mb:.2f}MB")

        # Audit log: successful upload
        log_audit_event(
            logger,
            "appimage_uploaded",
            session_id=session_id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "filename": safe_filename,
                "size_mb": f"{file_size_mb:.2f}",
                "original_filename": original_filename if original_filename != safe_filename else None
            }
        )

        log_file_operation(
            logger,
            "upload",
            str(file_path),
            session_id=session_id,
            success=True
        )

        # Check for existing signature info (without verification)
        signature_info = None

        try:
            verifier = AppImageVerifier()
            # Just get signature info, don't verify yet
            signature_info = verifier.get_signature_info(str(file_path))
            logger.debug(f"Signature info retrieved | session_id={session_id} | info={signature_info}")
        except Exception as e:
            logger.warning(f"Could not get signature info | session_id={session_id} | error={str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the upload, just return no signature info
            signature_info = {
                'has_signature': False,
                'error': f"Could not read signature: {str(e)}"
            }

        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content),
            "signature_info": signature_info
        }

    except Exception as e:
        session.error = str(e)
        logger.error(f"Upload failed | session_id={session_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/upload/key")
async def upload_key(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a GPG private key file"""

    if session_id not in sessions:
        logger.warning(f"Key upload with invalid session | session_id={session_id}")
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

        logger.info(f"Private key uploaded | session_id={session_id} | size={len(content)}")

        return {
            "status": "success",
            "message": "Key uploaded successfully"
        }

    except Exception as e:
        session.error = str(e)
        logger.error(f"Key upload failed | session_id={session_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Key upload failed: {str(e)}")


@app.post("/api/upload/signature")
async def upload_signature(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload the .asc signature file for the AppImage"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.appimage_path:
        raise HTTPException(status_code=400, detail="Upload AppImage first")

    # Save signature file next to AppImage
    signature_path = Path(str(session.appimage_path) + ".asc")

    try:
        async with aiofiles.open(signature_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # Verify the signature
        verifier = AppImageVerifier()
        result = verifier.verify_signature(str(session.appimage_path))

        return {
            "status": "success",
            "message": "Signature uploaded and verified",
            "verification": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signature upload failed: {str(e)}")


@app.post("/api/sign")
async def sign_appimage(
    session_id: str = Form(...),
    key_id: Optional[str] = Form(None),
    key_fingerprint: Optional[str] = Form(None),
    passphrase: Optional[str] = Form(None),
    embed_signature: bool = Form(False),
    background_tasks: BackgroundTasks = None
):
    """Sign the uploaded AppImage"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.appimage_path:
        raise HTTPException(status_code=400, detail="No AppImage uploaded")

    # Security: Warn if passphrase is empty
    if passphrase is not None and len(passphrase.strip()) == 0:
        logger.warning(f"Empty passphrase provided | session_id={session_id}")
        raise HTTPException(
            status_code=400,
            detail="Passphrase cannot be empty. If your key has no passphrase, omit the field."
        )

    try:
        # Priority 1: Use key_fingerprint if provided (from dropdown selection)
        if key_fingerprint:
            logger.info(f"Using selected key from keyring | session_id={session_id} | fingerprint={key_fingerprint[:16]}...")
            key_id = key_fingerprint

        # Priority 2: Import key if uploaded and get fingerprint
        elif session.key_path:
            manager = GPGKeyManager()
            try:
                fingerprint = manager.import_key_get_fingerprint(str(session.key_path))
                if fingerprint:
                    session.key_fingerprint = fingerprint
                    logger.info(f"Key imported | session_id={session_id} | fingerprint={fingerprint}")
                    # Use fingerprint as key_id if not provided
                    if not key_id:
                        key_id = fingerprint
                        logger.info(f"Using imported key fingerprint as key_id | session_id={session_id}")
                else:
                    raise HTTPException(status_code=400, detail="Failed to import GPG key")
            except ValueError as e:
                # Key validation failed (e.g., public key instead of private key)
                logger.error(f"Key validation failed | session_id={session_id} | error={str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid key: {str(e)}. Please upload a PRIVATE key, not a PUBLIC key."
                )

        # Priority 3: Use key_id if provided (manual entry)
        # (key_id is already set if provided)

        # Check if we have a key_id to use
        if not key_id:
            raise HTTPException(
                status_code=400,
                detail="No key provided. Please select a key, upload a GPG key, or enter a key ID."
            )

        # Initialize resigner
        resigner = AppImageResigner()

        # Sign the AppImage
        # Use original filename without session_id prefix since it's already in the session folder
        original_filename = session.appimage_path.name
        # Remove session_id prefix if it exists
        if original_filename.startswith(f"{session_id}_"):
            original_filename = original_filename[len(session_id) + 1:]

        output_path = SIGNED_DIR / f"{session_id}_{original_filename}"
        signature_path = Path(str(output_path) + ".asc")

        # Copy original to signed directory
        shutil.copy2(session.appimage_path, output_path)

        # Sign (passphrase will be used but not stored)
        success = resigner.sign_appimage(
            str(output_path),
            key_id=key_id,
            passphrase=passphrase,
            embed_signature=embed_signature
        )

        # Security: Overwrite passphrase in memory
        if passphrase:
            passphrase = "X" * len(passphrase)
            del passphrase

        if success:
            session.signed_path = output_path
            session.signature_path = signature_path
            session.status = "signed"

            # Verify signature
            logger.info(f"Verifying signature | session_id={session_id} | embed={embed_signature}")
            verifier = AppImageVerifier()
            verification = verifier.verify_signature(str(output_path))
            logger.info(f"Verification result | session_id={session_id} | valid={verification.get('valid')}")
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


@app.post("/api/verify/uploaded/{session_id}")
async def verify_uploaded_signature(session_id: str):
    """Verify the signature of an uploaded AppImage"""

    if session_id not in sessions:
        logger.warning(f"Verify with invalid session | session_id={session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.appimage_path:
        logger.warning(f"Verify without AppImage | session_id={session_id}")
        raise HTTPException(status_code=400, detail="No AppImage uploaded")

    try:
        verifier = AppImageVerifier()
        result = verifier.verify_signature(str(session.appimage_path))
        logger.info(f"Signature verified | session_id={session_id} | valid={result.get('valid')}")

        return {
            "status": "success",
            "verification": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")


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
async def download_appimage(session_id: str):
    """Download the signed AppImage"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.signed_path or not session.signed_path.exists():
        raise HTTPException(status_code=404, detail="Signed AppImage not found")

    # Remove UUID prefix from filename
    original_filename = session.signed_path.name
    if original_filename.startswith(f"{session_id}_"):
        original_filename = original_filename[len(session_id) + 1:]

    return FileResponse(
        session.signed_path,
        media_type="application/octet-stream",
        filename=original_filename
    )


@app.get("/api/download/signature/{session_id}")
async def download_signature(session_id: str):
    """Download the signature file"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.signature_path or not session.signature_path.exists():
        raise HTTPException(status_code=404, detail="Signature file not found")

    # Remove UUID prefix from filename
    original_filename = session.signature_path.name
    if original_filename.startswith(f"{session_id}_"):
        original_filename = original_filename[len(session_id) + 1:]

    return FileResponse(
        session.signature_path,
        media_type="application/pgp-signature",
        filename=original_filename
    )


@app.get("/api/download/zip/{session_id}")
async def download_zip(session_id: str):
    """Download both signed AppImage and signature as ZIP file"""
    import zipfile
    import tempfile

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session.signed_path or not session.signed_path.exists():
        raise HTTPException(status_code=404, detail="Signed AppImage not found")

    try:
        # Create temporary ZIP file
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.zip', delete=False) as tmp_zip:
            zip_path = Path(tmp_zip.name)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add AppImage
                appimage_name = session.signed_path.name
                if appimage_name.startswith(f"{session_id}_"):
                    appimage_name = appimage_name[len(session_id) + 1:]
                zipf.write(session.signed_path, appimage_name)

                # Add signature if exists
                if session.signature_path and session.signature_path.exists():
                    sig_name = session.signature_path.name
                    if sig_name.startswith(f"{session_id}_"):
                        sig_name = sig_name[len(session_id) + 1:]
                    zipf.write(session.signature_path, sig_name)

        # Get base filename without UUID and extension
        base_name = session.signed_path.stem
        if base_name.startswith(f"{session_id}_"):
            base_name = base_name[len(session_id) + 1:]

        zip_filename = f"{base_name}_signed.zip"

        logger.info(f"ZIP download | session_id={session_id} | filename={zip_filename}")

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_filename,
            background=BackgroundTasks().add_task(lambda: zip_path.unlink(missing_ok=True))
        )

    except Exception as e:
        logger.error(f"ZIP download failed | session_id={session_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {str(e)}")


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


# ============================================================================
# Key Management Endpoints
# ============================================================================

@app.post("/api/keys/import")
async def import_key(key_file: UploadFile = File(...)):
    """
    Import a GPG private key into the keyring.

    Args:
        key_file: Private key file (.asc)

    Returns:
        JSON with imported key metadata including fingerprint
    """
    try:
        # Validate file extension
        if not key_file.filename.endswith('.asc'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only .asc files are allowed."
            )

        # Read key content
        key_content = await key_file.read()
        key_content = key_content.decode('utf-8')

        logger.info(f"Key import attempt | filename={key_file.filename} | size={len(key_content)} bytes")

        # Import key
        from src.key_manager import GPGKeyManager
        manager = GPGKeyManager()
        fingerprint = manager.import_key_from_string(key_content)

        if not fingerprint:
            logger.error(f"Key import failed | filename={key_file.filename} | key_preview={key_content[:100]}")
            raise HTTPException(
                status_code=400,
                detail="Failed to import key. Please check the key format."
            )

        # Get key metadata
        from src.key_manager import get_key_by_fingerprint
        key_data = get_key_by_fingerprint(fingerprint)

        logger.info(
            f"Key imported | "
            f"filename={key_file.filename} | "
            f"fingerprint={fingerprint[:16]}... | "
            f"name={key_data.get('name', 'Unknown')}"
        )

        return {
            "success": True,
            "message": "Key imported successfully",
            "fingerprint": fingerprint,
            "key_data": key_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import key | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import key: {str(e)}")


@app.get("/api/keys/list")
async def list_keys():
    """
    List all GPG keys in the keyring.

    Returns:
        JSON with public and secret keys, including metadata
    """
    try:
        from src.key_manager import list_all_keys_with_metadata

        keys_data = list_all_keys_with_metadata()

        logger.info(
            f"Keys listed | "
            f"public_keys={keys_data['total_public']} | "
            f"secret_keys={keys_data['total_secret']}"
        )

        return keys_data

    except Exception as e:
        logger.error(f"Failed to list keys | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list keys: {str(e)}")


@app.get("/api/keys/{fingerprint}")
async def get_key_details(fingerprint: str):
    """
    Get detailed information about a specific key.

    Args:
        fingerprint: Key fingerprint

    Returns:
        JSON with key metadata
    """
    try:
        from src.key_manager import get_key_by_fingerprint

        key_data = get_key_by_fingerprint(fingerprint)

        if not key_data:
            raise HTTPException(status_code=404, detail="Key not found")

        logger.info(f"Key details retrieved | fingerprint={fingerprint[:16]}...")

        return key_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get key details | fingerprint={fingerprint} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get key details: {str(e)}")


@app.delete("/api/keys/{fingerprint}")
async def delete_key(fingerprint: str, delete_secret: bool = False):
    """
    Delete a key from the keyring.

    Args:
        fingerprint: Key fingerprint to delete
        delete_secret: If true, also delete secret key

    Returns:
        JSON with success status
    """
    try:
        from src.key_manager import delete_key_by_fingerprint

        result = delete_key_by_fingerprint(fingerprint, delete_secret)

        if result['success']:
            logger.info(
                f"Key deleted | "
                f"fingerprint={fingerprint[:16]}... | "
                f"delete_secret={delete_secret}"
            )
            return result
        else:
            logger.warning(
                f"Key deletion failed | "
                f"fingerprint={fingerprint} | "
                f"error={result.get('error')}"
            )
            raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete key | fingerprint={fingerprint} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")


# ============================================================================
# Streaming/Chunked Upload Endpoints
# ============================================================================

@app.post("/api/upload/init")
async def init_chunked_upload(
    session_id: str = Form(...),
    filename: str = Form(...),
    total_size: int = Form(...),
    file_type: str = Form("appimage")
):
    """
    Initialize a chunked upload session for large files.

    Args:
        session_id: Signing session ID
        filename: Original filename
        total_size: Total file size in bytes
        file_type: Type of file (appimage, key, signature)

    Returns:
        Upload session info with chunk details
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        upload_info = await StreamingUpload.init_upload(
            session_id=session_id,
            filename=filename,
            total_size=total_size,
            file_type=file_type
        )

        return upload_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to init upload | session_id={session_id} | "
            f"filename={filename} | error={str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to init upload: {str(e)}")


@app.post("/api/upload/chunk/{session_id}")
async def upload_chunk(
    session_id: str,
    chunk_number: str = Form(...),  # FormData sends as string
    checksum: Optional[str] = Form(None),
    chunk: UploadFile = File(...)
):
    """
    Upload a single file chunk.

    Args:
        session_id: Upload session ID
        chunk_number: Chunk number (0-indexed) as string
        checksum: Optional MD5/SHA-256 checksum for verification
        chunk: Chunk binary data

    Returns:
        Chunk upload status with progress
    """
    try:
        # Convert chunk_number to int
        chunk_num = int(chunk_number)

        logger.info(
            f"Chunk upload request | session_id={session_id} | "
            f"chunk_number={chunk_num} | checksum={checksum[:16] if checksum else 'none'}..."
        )

        # Read chunk data
        chunk_data = await chunk.read()

        logger.info(f"Chunk data read | size={len(chunk_data)} bytes")

        # Upload chunk
        result = await StreamingUpload.upload_chunk(
            session_id=session_id,
            chunk_number=chunk_num,
            chunk_data=chunk_data,
            checksum=checksum
        )

        return result

    except HTTPException as he:
        logger.error(
            f"HTTP Exception in chunk upload | session_id={session_id} | "
            f"chunk={chunk_number} | status={he.status_code} | detail={he.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"Failed to upload chunk | session_id={session_id} | "
            f"chunk={chunk_number} | error={str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to upload chunk: {str(e)}")


@app.post("/api/upload/complete/{session_id}")
async def complete_chunked_upload(
    session_id: str,
    file_type: str = Form("appimage")
):
    """
    Complete chunked upload and merge chunks into final file.

    Args:
        session_id: Upload session ID
        file_type: Type of file (appimage, key, signature)

    Returns:
        Upload completion status with file info
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    try:
        # Determine target directory based on file type
        if file_type == "key":
            target_dir = TEMP_KEYS_DIR
        else:
            target_dir = UPLOAD_DIR

        # Complete upload
        final_path = await StreamingUpload.complete_upload(
            session_id=session_id,
            target_dir=target_dir
        )

        # Update session with file path
        if file_type == "appimage":
            session.appimage_path = final_path
            session.status = "appimage_uploaded"

            # Validate AppImage
            is_valid, error_msg = validate_appimage_file(
                final_path,
                max_size_bytes=MAX_FILE_SIZE,
                check_elf=True,
                check_appimage=True
            )

            if not is_valid:
                final_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=f"Invalid AppImage: {error_msg}")

            # Get signature info
            try:
                verifier = AppImageVerifier()
                signature_info = verifier.get_signature_info(str(final_path))
            except Exception as e:
                signature_info = {
                    'has_signature': False,
                    'error': f"Could not read signature: {str(e)}"
                }

            return {
                "status": "success",
                "filename": final_path.name,
                "size": final_path.stat().st_size,
                "signature_info": signature_info
            }

        elif file_type == "key":
            session.key_path = final_path
            session.status = "key_uploaded"

            return {
                "status": "success",
                "message": "Key uploaded successfully",
                "size": final_path.stat().st_size
            }

        else:
            return {
                "status": "success",
                "filename": final_path.name,
                "size": final_path.stat().st_size
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to complete upload | session_id={session_id} | error={str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")


@app.get("/api/upload/status/{session_id}")
async def get_upload_status(session_id: str):
    """
    Get status of chunked upload.

    Args:
        session_id: Upload session ID

    Returns:
        Upload progress and status
    """
    try:
        status = StreamingUpload.get_upload_status(session_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status | session_id={session_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# ============================================================================
# End Streaming Upload Endpoints
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    # Clean up old sessions
    cleanup_old_sessions()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
