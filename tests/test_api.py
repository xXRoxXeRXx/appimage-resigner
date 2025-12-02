"""
API Endpoint Tests
Tests for FastAPI web application endpoints
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import io


# Import app only when tests run (avoids import issues in CI)
@pytest.fixture
def client():
    """Create test client for API testing"""
    from web.app import app
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test that health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "gpg" in data
        assert "sessions" in data

    def test_health_check_contains_gpg_info(self, client):
        """Test that health check includes GPG availability"""
        response = client.get("/health")
        data = response.json()

        assert "gpg" in data
        assert "available" in data["gpg"]


class TestSessionEndpoints:
    """Test session management endpoints"""

    def test_create_session(self, client):
        """Test session creation"""
        response = client.post("/api/session/create")
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["status"] == "created"
        assert "expires_in_hours" in data

    def test_create_multiple_sessions(self, client):
        """Test that multiple sessions can be created"""
        response1 = client.post("/api/session/create")
        response2 = client.post("/api/session/create")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Sessions should have different IDs
        assert data1["session_id"] != data2["session_id"]


class TestUploadEndpoints:
    """Test file upload endpoints"""

    def test_upload_without_session(self, client):
        """Test that upload fails without valid session"""
        # Create a minimal AppImage-like file
        file_content = b'\x7fELF\x02\x02\x02\x02AI\x02' + b'\x00' * 1000

        response = client.post(
            "/api/upload/appimage",
            data={"session_id": "invalid-session-id"},
            files={"file": ("test.AppImage", io.BytesIO(file_content), "application/octet-stream")}
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_upload_invalid_extension(self, client):
        """Test that upload fails with wrong file extension"""
        # Create session first
        session_response = client.post("/api/session/create")
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/api/upload/appimage",
            data={"session_id": session_id},
            files={"file": ("test.txt", io.BytesIO(b"not an appimage"), "text/plain")}
        )

        assert response.status_code == 400
        assert "AppImage" in response.json()["detail"]


class TestStaticFiles:
    """Test static file serving"""

    def test_index_html(self, client):
        """Test that index.html is served"""
        response = client.get("/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_css_file(self, client):
        """Test that CSS files are served"""
        response = client.get("/static/style.css")
        assert response.status_code == 200

    def test_js_file(self, client):
        """Test that JS files are served"""
        response = client.get("/static/app.js")
        assert response.status_code == 200


class TestSecurityHeaders:
    """Test security headers are present"""

    def test_csp_header(self, client):
        """Test Content-Security-Policy header"""
        response = client.get("/health")
        assert "content-security-policy" in response.headers

    def test_xframe_options(self, client):
        """Test X-Frame-Options header"""
        response = client.get("/health")
        assert response.headers.get("x-frame-options") == "DENY"

    def test_content_type_options(self, client):
        """Test X-Content-Type-Options header"""
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_xss_protection(self, client):
        """Test X-XSS-Protection header"""
        response = client.get("/health")
        assert "x-xss-protection" in response.headers
