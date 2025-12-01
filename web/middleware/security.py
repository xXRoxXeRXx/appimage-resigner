#!/usr/bin/env python3
"""
Security Middleware for AppImage Re-Signer
Implements various security measures including CSP, CSRF protection, and security headers
"""

from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import secrets
import hashlib
from datetime import datetime, timedelta

from web.core.logging_config import get_logger
from web.core.config import settings

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    
    Implements:
    - Content Security Policy (CSP)
    - X-Frame-Options (Clickjacking Protection)
    - X-Content-Type-Options (MIME Sniffing Protection)
    - X-XSS-Protection (Legacy XSS Protection)
    - Referrer-Policy
    - Strict-Transport-Security (HSTS)
    - Permissions-Policy
    """
    
    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        csp_report_only: bool = False,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.csp_report_only = csp_report_only
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Content Security Policy
        if self.enable_csp:
            csp_header = "Content-Security-Policy" if not self.csp_report_only else "Content-Security-Policy-Report-Only"
            
            # CSP directives
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline'",  # unsafe-inline needed for inline scripts
                "style-src 'self' 'unsafe-inline'",   # unsafe-inline needed for inline styles
                "img-src 'self' data:",               # data: for inline images
                "font-src 'self'",
                "connect-src 'self'",                 # API calls to same origin
                "frame-ancestors 'none'",             # Prevent framing
                "base-uri 'self'",
                "form-action 'self'",
            ]
            
            response.headers[csp_header] = "; ".join(csp_directives)
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection: Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Strict-Transport-Security (HSTS): Force HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains"
        
        # Permissions-Policy: Control browser features
        permissions = [
            "geolocation=()",      # Disable geolocation
            "microphone=()",       # Disable microphone
            "camera=()",           # Disable camera
            "payment=()",          # Disable payment
            "usb=()",              # Disable USB
            "magnetometer=()",     # Disable magnetometer
            "gyroscope=()",        # Disable gyroscope
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware
    
    Generates and validates CSRF tokens for state-changing operations (POST, PUT, DELETE, PATCH)
    Tokens are stored in session and validated via header or form data
    """
    
    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Paths that are exempt from CSRF protection
    EXEMPT_PATHS = {
        "/health",
        "/api/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    def __init__(self, app, token_header: str = "X-CSRF-Token"):
        super().__init__(app)
        self.token_header = token_header
        self.tokens = {}  # In production: use Redis or database
        
    def generate_token(self) -> str:
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(32)
    
    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token for protected methods"""
        
        # Skip CSRF check for exempt paths
        if self.is_exempt(request.url.path):
            return await call_next(request)
        
        # Skip CSRF check for safe methods (GET, HEAD, OPTIONS)
        if request.method not in self.PROTECTED_METHODS:
            response = await call_next(request)
            
            # Add CSRF token to response headers for GET requests
            # Frontend can read this and include it in subsequent requests
            csrf_token = self.generate_token()
            
            # Store token with session identifier
            session_id = request.cookies.get("session_id")
            if session_id:
                self.tokens[session_id] = {
                    "token": csrf_token,
                    "expires": datetime.utcnow() + timedelta(hours=24)
                }
            
            response.headers[self.token_header] = csrf_token
            return response
        
        # Validate CSRF token for protected methods
        session_id = request.cookies.get("session_id")
        if not session_id:
            logger.warning(f"CSRF: Missing session_id for {request.method} {request.url.path}")
            # For now, just log warning - don't block (for backward compatibility)
            # In production, you might want to raise HTTPException
            return await call_next(request)
        
        # Get token from header or form data
        token_from_header = request.headers.get(self.token_header)
        
        # Get stored token
        stored_token_data = self.tokens.get(session_id)
        
        if not stored_token_data:
            logger.warning(f"CSRF: No stored token for session {session_id}")
            # For now, just log warning
            return await call_next(request)
        
        # Check if token is expired
        if datetime.utcnow() > stored_token_data["expires"]:
            logger.warning(f"CSRF: Token expired for session {session_id}")
            del self.tokens[session_id]
            # For now, just log warning
            return await call_next(request)
        
        # Validate token
        if token_from_header and secrets.compare_digest(token_from_header, stored_token_data["token"]):
            logger.debug(f"CSRF: Token validated for {request.method} {request.url.path}")
            return await call_next(request)
        
        logger.warning(
            f"CSRF: Invalid token for {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # For now, just log warning - don't block requests
        # TODO: Enable strict CSRF protection in production
        # raise HTTPException(
        #     status_code=status.HTTP_403_FORBIDDEN,
        #     detail="CSRF token validation failed"
        # )
        
        return await call_next(request)


class FileSizeValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce file size limits before processing uploads
    This is a safety net in addition to client-side and endpoint-level validation
    """
    
    def __init__(self, app, max_size: int = 2 * 1024 * 1024 * 1024):  # 2GB default
        super().__init__(app)
        self.max_size = max_size
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check Content-Length header for file uploads"""
        
        # Only check for file upload endpoints
        if request.url.path.startswith("/api/upload"):
            content_length = request.headers.get("content-length")
            
            if content_length:
                content_length = int(content_length)
                
                if content_length > self.max_size:
                    logger.warning(
                        f"File size limit exceeded: {content_length / (1024**3):.2f}GB > "
                        f"{self.max_size / (1024**3):.2f}GB from {request.client.host if request.client else 'unknown'}"
                    )
                    
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"File too large. Maximum size: {self.max_size / (1024**3):.2f}GB"
                        }
                    )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware
    In production, use Redis-based rate limiting (e.g., slowapi)
    """
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production: use Redis
        
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier (IP address)"""
        # Try to get real IP from X-Forwarded-For header (if behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit for client"""
        
        client_id = self.get_client_identifier(request)
        now = datetime.utcnow()
        
        # Clean up old entries
        self.requests = {
            k: v for k, v in self.requests.items()
            if (now - v["window_start"]).total_seconds() < self.window_seconds
        }
        
        # Initialize client data if not exists
        if client_id not in self.requests:
            self.requests[client_id] = {
                "count": 0,
                "window_start": now
            }
        
        client_data = self.requests[client_id]
        
        # Check if window has expired
        if (now - client_data["window_start"]).total_seconds() >= self.window_seconds:
            client_data["count"] = 0
            client_data["window_start"] = now
        
        # Increment request count
        client_data["count"] += 1
        
        # Check rate limit
        if client_data["count"] > self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {client_id}: "
                f"{client_data['count']} requests in {self.window_seconds}s"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."
                },
                headers={
                    "Retry-After": str(self.window_seconds)
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - client_data["count"])
        response.headers["X-RateLimit-Reset"] = str(
            int((client_data["window_start"] + timedelta(seconds=self.window_seconds)).timestamp())
        )
        
        return response
