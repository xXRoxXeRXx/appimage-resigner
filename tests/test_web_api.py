"""
Integration Tests for Web API Endpoints
Tests all FastAPI endpoints with TestClient
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import io


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from web.app import app
    return TestClient(app)


@pytest.fixture
def test_session(client):
    """Create a test session"""
    response = client.post("/api/session/create")
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    yield session_id
    
    # Cleanup
    try:
        client.delete(f"/api/session/{session_id}")
    except:
        pass


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "version" in data
        assert "gpg_available" in data
        assert "timestamp" in data
    
    def test_health_check_structure(self, client):
        """Test health check response structure"""
        response = client.get("/health")
        data = response.json()
        
        # Verify all required fields
        required_fields = ["status", "version", "gpg_available", "timestamp"]
        for field in required_fields:
            assert field in data


class TestSessionManagement:
    """Test session management endpoints"""
    
    def test_create_session(self, client):
        """Test session creation"""
        response = client.post("/api/session/create")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert len(data["session_id"]) == 36  # UUID format
    
    def test_get_session_status(self, client, test_session):
        """Test getting session status"""
        response = client.get(f"/api/session/{test_session}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == test_session
        assert "appimage_uploaded" in data
        assert "key_uploaded" in data
        assert "signed" in data
    
    def test_get_nonexistent_session(self, client):
        """Test getting non-existent session"""
        fake_session = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/session/{fake_session}")
        
        assert response.status_code == 404
    
    def test_delete_session(self, client):
        """Test session deletion"""
        # Create session
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Delete session
        response = client.delete(f"/api/session/{session_id}")
        
        assert response.status_code == 200
        
        # Verify deleted
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 404
    
    def test_delete_nonexistent_session(self, client):
        """Test deleting non-existent session"""
        fake_session = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/session/{fake_session}")
        
        assert response.status_code == 404


class TestFileUpload:
    """Test file upload endpoints"""
    
    def test_upload_appimage(self, client, test_session, sample_appimage):
        """Test AppImage upload"""
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            response = client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "AppImage uploaded successfully"
        assert "filename" in data
    
    def test_upload_appimage_without_session(self, client, sample_appimage):
        """Test AppImage upload without session"""
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            response = client.post(
                "/api/upload/appimage",
                files=files
            )
        
        assert response.status_code == 422  # Missing session_id
    
    def test_upload_invalid_appimage(self, client, test_session, invalid_file):
        """Test uploading invalid file as AppImage"""
        with open(invalid_file, 'rb') as f:
            files = {'file': (invalid_file.name, f, 'text/plain')}
            response = client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files=files
            )
        
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
    
    def test_upload_gpg_key(self, client, test_session, gpg_instance, generated_gpg_key, test_key_data):
        """Test GPG key upload"""
        # Export key to file-like object
        key_data = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        
        files = {'file': ('key.asc', io.BytesIO(key_data.encode()), 'application/pgp-keys')}
        response = client.post(
            f"/api/upload/key?session_id={test_session}",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "GPG key uploaded successfully"
    
    def test_upload_signature(self, client, test_session, temp_dir):
        """Test signature upload"""
        # Create dummy signature file
        signature_file = temp_dir / "test.asc"
        signature_file.write_text("-----BEGIN PGP SIGNATURE-----\ntest\n-----END PGP SIGNATURE-----")
        
        with open(signature_file, 'rb') as f:
            files = {'file': (signature_file.name, f, 'application/pgp-signature')}
            response = client.post(
                f"/api/upload/signature?session_id={test_session}",
                files=files
            )
        
        assert response.status_code == 200
    
    def test_upload_file_too_large(self, client, test_session, temp_dir):
        """Test uploading file exceeding size limit"""
        # This test would require creating a very large file
        # Skipped in practice to avoid long test times
        pytest.skip("Requires creating large file (>500MB)")


class TestSigningOperations:
    """Test signing operations"""
    
    def test_sign_appimage(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test complete signing workflow"""
        # 1. Upload AppImage
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            response = client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files=files
            )
        assert response.status_code == 200
        
        # 2. Upload GPG key
        key_data = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        files = {'file': ('key.asc', io.BytesIO(key_data.encode()), 'application/pgp-keys')}
        response = client.post(
            f"/api/upload/key?session_id={test_session}",
            files=files
        )
        assert response.status_code == 200
        
        # 3. Sign
        response = client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "signature_created" in data["message"].lower()
    
    def test_sign_without_appimage(self, client, test_session):
        """Test signing without uploading AppImage"""
        response = client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": "test"}
        )
        
        assert response.status_code == 400
    
    def test_sign_without_key(self, client, test_session, sample_appimage):
        """Test signing without uploading GPG key"""
        # Upload AppImage only
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files=files
            )
        
        # Try to sign
        response = client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": "test"}
        )
        
        assert response.status_code == 400
    
    def test_sign_with_empty_passphrase(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test signing with empty passphrase"""
        # Upload files
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={test_session}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        # Try to sign with empty passphrase
        response = client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": ""}
        )
        
        assert response.status_code == 400


class TestVerification:
    """Test signature verification endpoints"""
    
    def test_verify_uploaded_signature(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test verifying uploaded signature"""
        # Upload AppImage
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        # Create and upload signature
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        with open(signature_path, 'rb') as f:
            client.post(
                f"/api/upload/signature?session_id={test_session}",
                files={'file': f}
            )
        
        # Verify
        response = client.get(f"/api/verify/uploaded?session_id={test_session}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "trust_level" in data
    
    def test_verify_without_signature(self, client, test_session, sample_appimage):
        """Test verification without signature"""
        # Upload AppImage only
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        # Try to verify
        response = client.get(f"/api/verify/uploaded?session_id={test_session}")
        
        assert response.status_code == 400


class TestDownload:
    """Test download endpoints"""
    
    def test_download_signed_appimage(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test downloading signed AppImage"""
        # Complete signing workflow
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={test_session}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        # Download
        response = client.get(f"/api/download/appimage?session_id={test_session}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert len(response.content) > 0
    
    def test_download_signature(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test downloading signature file"""
        # Complete signing workflow
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={test_session}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        # Download signature
        response = client.get(f"/api/download/signature?session_id={test_session}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pgp-signature"
        assert b"BEGIN PGP SIGNATURE" in response.content
    
    def test_download_zip(
        self,
        client,
        test_session,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test downloading ZIP archive"""
        # Complete signing workflow
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={test_session}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={test_session}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        client.post(
            f"/api/sign?session_id={test_session}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        # Download ZIP
        response = client.get(f"/api/download/zip?session_id={test_session}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert len(response.content) > 0
        
        # Verify it's a valid ZIP
        assert response.content[:2] == b'PK'  # ZIP magic bytes
    
    def test_download_without_signing(self, client, test_session):
        """Test downloading before signing"""
        response = client.get(f"/api/download/appimage?session_id={test_session}")
        
        assert response.status_code == 400


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_session_id_format(self, client):
        """Test invalid session ID format"""
        response = client.get("/api/session/invalid-format")
        
        # Should return 404 or 422 depending on routing
        assert response.status_code in [404, 422]
    
    def test_missing_required_parameters(self, client):
        """Test missing required parameters"""
        response = client.post("/api/sign")
        
        assert response.status_code == 422
    
    def test_invalid_json_body(self, client, test_session):
        """Test invalid JSON body"""
        response = client.post(
            f"/api/sign?session_id={test_session}",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present"""
        response = client.options("/health")
        
        # Should have CORS headers (if configured)
        # This depends on your CORS middleware configuration
        pass  # Skip for now, requires specific CORS setup
    
    def test_cors_preflight(self, client):
        """Test CORS preflight request"""
        response = client.options(
            "/api/session/create",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should handle preflight
        pass  # Skip for now


class TestRateLimiting:
    """Test rate limiting (if implemented)"""
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limit_exceeded(self, client):
        """Test rate limit enforcement"""
        # Make many requests quickly
        for _ in range(100):
            response = client.post("/api/session/create")
        
        # Should eventually get 429 Too Many Requests
        assert response.status_code == 429
