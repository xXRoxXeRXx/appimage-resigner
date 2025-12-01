#!/usr/bin/env python3
"""
Streaming Upload Service for Large Files
Provides chunked upload, resume support, and memory-efficient file operations
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime

import aiofiles
from fastapi import UploadFile, HTTPException

from web.core.logging_config import get_logger
from web.core.config import settings

logger = get_logger(__name__)


class ChunkInfo:
    """Information about an upload chunk"""

    def __init__(self, chunk_number: int, total_chunks: int, chunk_size: int):
        self.chunk_number = chunk_number
        self.total_chunks = total_chunks
        self.chunk_size = chunk_size
        self.uploaded_at = datetime.now()
        self.checksum: Optional[str] = None


class StreamingUpload:
    """Manages chunked/streaming uploads for large files"""

    # In-memory storage for upload sessions (use Redis in production)
    upload_sessions: Dict[str, Dict[str, Any]] = {}

    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
    MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB max per chunk

    @classmethod
    async def init_upload(
        cls,
        session_id: str,
        filename: str,
        total_size: int,
        file_type: str = "appimage"
    ) -> Dict[str, Any]:
        """
        Initialize a chunked upload session

        Args:
            session_id: Unique session identifier
            filename: Original filename
            total_size: Total file size in bytes
            file_type: Type of file (appimage, key, signature)

        Returns:
            Upload session info with chunk details
        """
        if total_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_file_size} MB"
            )

        # Calculate number of chunks
        total_chunks = (total_size + cls.CHUNK_SIZE - 1) // cls.CHUNK_SIZE

        # Create temporary upload directory
        upload_dir = settings.upload_dir / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session
        upload_session = {
            "session_id": session_id,
            "filename": filename,
            "file_type": file_type,
            "total_size": total_size,
            "total_chunks": total_chunks,
            "chunk_size": cls.CHUNK_SIZE,
            "uploaded_chunks": {},
            "upload_dir": str(upload_dir),
            "started_at": datetime.now().isoformat(),
            "completed": False,
            "final_path": None
        }

        cls.upload_sessions[session_id] = upload_session

        logger.info(
            f"Upload initialized | session_id={session_id} | "
            f"filename={filename} | size={total_size} | chunks={total_chunks}"
        )

        return {
            "session_id": session_id,
            "total_chunks": total_chunks,
            "chunk_size": cls.CHUNK_SIZE,
            "upload_url": f"/api/upload/chunk/{session_id}"
        }

    @classmethod
    async def upload_chunk(
        cls,
        session_id: str,
        chunk_number: int,
        chunk_data: bytes,
        checksum: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a single chunk

        Args:
            session_id: Upload session ID
            chunk_number: Chunk number (0-indexed)
            chunk_data: Chunk binary data
            checksum: Optional MD5 checksum for verification

        Returns:
            Chunk upload status
        """
        if session_id not in cls.upload_sessions:
            logger.error(
                f"Upload session not found | session_id={session_id} | "
                f"available_sessions={list(cls.upload_sessions.keys())}"
            )
            raise HTTPException(status_code=404, detail="Upload session not found")

        session = cls.upload_sessions[session_id]

        # Validate chunk number
        if chunk_number >= session["total_chunks"]:
            raise HTTPException(status_code=400, detail="Invalid chunk number")

        # Validate chunk size
        if len(chunk_data) > cls.MAX_CHUNK_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Chunk too large. Max: {cls.MAX_CHUNK_SIZE / 1024 / 1024} MB"
            )

        # Verify checksum if provided
        if checksum:
            # Try SHA-256 first (modern browsers use this)
            actual_checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()
            # Fallback to MD5 for compatibility
            actual_checksum_md5 = hashlib.md5(chunk_data).hexdigest()

            if actual_checksum_sha256 != checksum and actual_checksum_md5 != checksum:
                logger.error(
                    "Checksum mismatch | "
                    f"received={checksum[:16]}... | "
                    f"sha256={actual_checksum_sha256[:16]}... | "
                    f"md5={actual_checksum_md5[:16]}..."
                )
                raise HTTPException(
                    status_code=400,
                    detail="Chunk checksum mismatch"
                )

        # Write chunk to temporary file
        chunk_path = Path(session["upload_dir"]) / f"chunk_{chunk_number:04d}"

        try:
            async with aiofiles.open(chunk_path, 'wb') as f:
                await f.write(chunk_data)

            # Store chunk info
            session["uploaded_chunks"][chunk_number] = {
                "size": len(chunk_data),
                "checksum": checksum or hashlib.md5(chunk_data).hexdigest(),
                "uploaded_at": datetime.now().isoformat()
            }

            uploaded_count = len(session["uploaded_chunks"])
            progress = (uploaded_count / session["total_chunks"]) * 100

            logger.debug(
                f"Chunk uploaded | session_id={session_id} | "
                f"chunk={chunk_number}/{session['total_chunks']} | "
                f"size={len(chunk_data)} | progress={progress:.1f}%"
            )

            return {
                "status": "chunk_uploaded",
                "chunk_number": chunk_number,
                "uploaded_chunks": uploaded_count,
                "total_chunks": session["total_chunks"],
                "progress": progress,
                "complete": uploaded_count == session["total_chunks"]
            }

        except Exception as e:
            logger.error(
                f"Chunk upload failed | session_id={session_id} | "
                f"chunk={chunk_number} | error={str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save chunk: {str(e)}"
            )

    @classmethod
    async def complete_upload(
        cls,
        session_id: str,
        target_dir: Path
    ) -> Path:
        """
        Merge all chunks into final file

        Args:
            session_id: Upload session ID
            target_dir: Target directory for final file

        Returns:
            Path to final merged file
        """
        if session_id not in cls.upload_sessions:
            raise HTTPException(status_code=404, detail="Upload session not found")

        session = cls.upload_sessions[session_id]

        # Check all chunks are uploaded
        if len(session["uploaded_chunks"]) != session["total_chunks"]:
            missing = session["total_chunks"] - len(session["uploaded_chunks"])
            raise HTTPException(
                status_code=400,
                detail=f"Upload incomplete. Missing {missing} chunks"
            )

        # Create final file path
        final_path = target_dir / f"{session_id}_{session['filename']}"

        try:
            # Merge chunks
            async with aiofiles.open(final_path, 'wb') as out_file:
                for chunk_num in range(session["total_chunks"]):
                    chunk_path = Path(session["upload_dir"]) / f"chunk_{chunk_num:04d}"

                    if not chunk_path.exists():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Chunk {chunk_num} not found"
                        )

                    # Read and write chunk (memory efficient)
                    async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                        while True:
                            data = await chunk_file.read(1024 * 1024)  # 1MB buffer
                            if not data:
                                break
                            await out_file.write(data)

                    # Clean up chunk
                    chunk_path.unlink()

            # Cleanup upload directory
            upload_dir = Path(session["upload_dir"])
            if upload_dir.exists():
                upload_dir.rmdir()

            # Update session
            session["completed"] = True
            session["final_path"] = str(final_path)

            logger.info(
                f"Upload completed | session_id={session_id} | "
                f"final_path={final_path} | size={final_path.stat().st_size}"
            )

            return final_path

        except Exception as e:
            logger.error(
                f"Upload completion failed | session_id={session_id} | error={str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete upload: {str(e)}"
            )

    @classmethod
    def get_upload_status(cls, session_id: str) -> Dict[str, Any]:
        """Get upload session status"""
        if session_id not in cls.upload_sessions:
            raise HTTPException(status_code=404, detail="Upload session not found")

        session = cls.upload_sessions[session_id]
        uploaded = len(session["uploaded_chunks"])
        total = session["total_chunks"]

        return {
            "session_id": session_id,
            "filename": session["filename"],
            "total_size": session["total_size"],
            "uploaded_chunks": uploaded,
            "total_chunks": total,
            "progress": (uploaded / total * 100) if total > 0 else 0,
            "completed": session["completed"],
            "started_at": session["started_at"]
        }

    @classmethod
    def cleanup_session(cls, session_id: str) -> bool:
        """Clean up upload session and temporary files"""
        if session_id not in cls.upload_sessions:
            return False

        session = cls.upload_sessions[session_id]

        # Remove chunk files
        upload_dir = Path(session["upload_dir"])
        if upload_dir.exists():
            for chunk_file in upload_dir.glob("chunk_*"):
                chunk_file.unlink(missing_ok=True)
            upload_dir.rmdir()

        # Remove session
        del cls.upload_sessions[session_id]

        logger.info(f"Upload session cleaned up | session_id={session_id}")
        return True


async def stream_large_file(
    file_path: Path,
    chunk_size: int = 8192
):
    """
    Async generator for streaming large files

    Args:
        file_path: Path to file
        chunk_size: Chunk size for streaming (default 8KB)

    Yields:
        File chunks as bytes
    """
    async with aiofiles.open(file_path, 'rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk
