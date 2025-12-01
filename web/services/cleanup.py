"""
Cleanup Service
Handles session and file cleanup operations.
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta

from web.core.config import settings
from web.core.logging_config import get_logger

logger = get_logger(__name__)


class CleanupService:
    """Service for cleaning up old sessions and files."""
    
    def __init__(self, sessions: Dict[str, Any]):
        """Initialize cleanup service.
        
        Args:
            sessions: Dictionary of active sessions
        """
        self.sessions = sessions
    
    def cleanup_session(self, session_id: str) -> int:
        """Clean up a specific session.
        
        Args:
            session_id: Session ID to clean up
            
        Returns:
            Number of files deleted
        """
        if session_id not in self.sessions:
            return 0
        
        session = self.sessions[session_id]
        files_deleted = 0
        
        # Delete files
        for attr in ['appimage_path', 'key_path', 'signed_path', 'signature_path']:
            file_path = getattr(session, attr, None)
            if file_path and isinstance(file_path, Path) and file_path.exists():
                try:
                    file_path.unlink()
                    files_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
        
        # Remove from sessions
        del self.sessions[session_id]
        logger.info(f"Session cleaned up | session_id={session_id} | files_deleted={files_deleted}")
        
        return files_deleted
    
    def cleanup_old_sessions(self) -> int:
        """Clean up sessions older than configured threshold.
        
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=settings.cleanup_after_hours)
        
        old_sessions = [
            sid for sid, session in self.sessions.items()
            if hasattr(session, 'created_at') and session.created_at < cutoff_time
        ]
        
        if old_sessions:
            logger.info(f"Cleaning up {len(old_sessions)} old sessions")
        
        for sid in old_sessions:
            self.cleanup_session(sid)
        
        return len(old_sessions)
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics.
        
        Returns:
            Dictionary with cleanup stats
        """
        return {
            "active_sessions": len(self.sessions),
            "cleanup_after_hours": settings.cleanup_after_hours,
            "cutoff_time": datetime.now() - timedelta(hours=settings.cleanup_after_hours)
        }
