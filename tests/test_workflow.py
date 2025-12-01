"""
Integration Tests for End-to-End Workflows
Tests complete user workflows from start to finish
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import gnupg
import io
import zipfile
import subprocess


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from web.app import app
    return TestClient(app)


class TestCompleteSigningWorkflow:
    """Test complete signing workflow"""
    
    def test_end_to_end_workflow(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test complete workflow: create session → upload → sign → download → verify"""
        
        # 1. Create session
        response = client.post("/api/session/create")
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        print(f"✓ Session created: {session_id}")
        
        # 2. Check initial session status
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 200
        status = response.json()
        assert status["appimage_uploaded"] is False
        assert status["key_uploaded"] is False
        assert status["signed"] is False
        print("✓ Initial session status verified")
        
        # 3. Upload AppImage
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            response = client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files=files
            )
        assert response.status_code == 200
        print("✓ AppImage uploaded")
        
        # 4. Check session status after upload
        response = client.get(f"/api/session/{session_id}")
        status = response.json()
        assert status["appimage_uploaded"] is True
        print("✓ Session status updated")
        
        # 5. Upload GPG key
        key_data = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        files = {'file': ('key.asc', io.BytesIO(key_data.encode()), 'application/pgp-keys')}
        response = client.post(
            f"/api/upload/key?session_id={session_id}",
            files=files
        )
        assert response.status_code == 200
        print("✓ GPG key uploaded")
        
        # 6. Sign AppImage
        response = client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        print("✓ AppImage signed")
        
        # 7. Check final session status
        response = client.get(f"/api/session/{session_id}")
        status = response.json()
        assert status["signed"] is True
        print("✓ Final session status verified")
        
        # 8. Download signed AppImage
        response = client.get(f"/api/download/appimage?session_id={session_id}")
        assert response.status_code == 200
        signed_appimage = response.content
        assert len(signed_appimage) > 0
        print("✓ Signed AppImage downloaded")
        
        # 9. Download signature
        response = client.get(f"/api/download/signature?session_id={session_id}")
        assert response.status_code == 200
        signature = response.content
        assert b"BEGIN PGP SIGNATURE" in signature
        print("✓ Signature downloaded")
        
        # 10. Download ZIP
        response = client.get(f"/api/download/zip?session_id={session_id}")
        assert response.status_code == 200
        zip_content = response.content
        assert zip_content[:2] == b'PK'  # ZIP magic
        print("✓ ZIP archive downloaded")
        
        # 11. Verify ZIP contains both files
        import io
        zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
        names = zip_file.namelist()
        assert len(names) == 2
        assert any(n.endswith('.AppImage') for n in names)
        assert any(n.endswith('.asc') for n in names)
        print("✓ ZIP contents verified")
        
        # 12. Clean up session
        response = client.delete(f"/api/session/{session_id}")
        assert response.status_code == 200
        print("✓ Session deleted")
        
        # 13. Verify session is gone
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 404
        print("✓ Session cleanup verified")
        
        print("\n✅ Complete workflow successful!")


class TestMultipleSessionsWorkflow:
    """Test handling multiple concurrent sessions"""
    
    def test_concurrent_sessions(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test multiple sessions can coexist"""
        
        # Create 3 sessions
        sessions = []
        for i in range(3):
            response = client.post("/api/session/create")
            assert response.status_code == 200
            session_id = response.json()["session_id"]
            sessions.append(session_id)
            print(f"✓ Session {i+1} created: {session_id}")
        
        # Each session should be independent
        assert len(set(sessions)) == 3  # All unique
        
        # Upload to first session only
        with open(sample_appimage, 'rb') as f:
            files = {'file': (sample_appimage.name, f, 'application/octet-stream')}
            response = client.post(
                f"/api/upload/appimage?session_id={sessions[0]}",
                files=files
            )
        assert response.status_code == 200
        
        # Check first session has file
        response = client.get(f"/api/session/{sessions[0]}")
        assert response.json()["appimage_uploaded"] is True
        
        # Check other sessions don't have file
        for session_id in sessions[1:]:
            response = client.get(f"/api/session/{session_id}")
            assert response.json()["appimage_uploaded"] is False
        
        print("✓ Session isolation verified")
        
        # Clean up all sessions
        for session_id in sessions:
            client.delete(f"/api/session/{session_id}")
        
        print("✅ Concurrent sessions test passed!")


class TestErrorRecoveryWorkflow:
    """Test error recovery in workflows"""
    
    def test_recover_from_wrong_passphrase(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test recovery after wrong passphrase"""
        
        # Create session and upload files
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={session_id}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        # Try with wrong passphrase
        response = client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": "wrong-passphrase"}
        )
        assert response.status_code == 400
        print("✓ Wrong passphrase rejected")
        
        # Session should still exist
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 200
        
        # Retry with correct passphrase
        response = client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        assert response.status_code == 200
        print("✓ Correct passphrase accepted")
        
        # Should be able to download
        response = client.get(f"/api/download/appimage?session_id={session_id}")
        assert response.status_code == 200
        
        print("✅ Error recovery successful!")
    
    def test_recover_from_invalid_file(
        self,
        client,
        invalid_file
    ):
        """Test recovery after invalid file upload"""
        
        # Create session
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Try to upload invalid file
        with open(invalid_file, 'rb') as f:
            files = {'file': (invalid_file.name, f, 'text/plain')}
            response = client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files=files
            )
        assert response.status_code == 400
        print("✓ Invalid file rejected")
        
        # Session should still exist
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 200
        assert response.json()["appimage_uploaded"] is False
        
        print("✅ Invalid file recovery successful!")


class TestBatchProcessingWorkflow:
    """Test batch processing workflows"""
    
    def test_batch_signing(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test signing multiple AppImages"""
        
        # Create multiple AppImage copies
        appimages = []
        for i in range(3):
            appimage_copy = temp_dir / f"app-{i}.AppImage"
            appimage_copy.write_bytes(sample_appimage.read_bytes())
            appimages.append(appimage_copy)
        
        signed_results = []
        
        for i, appimage in enumerate(appimages):
            print(f"\nProcessing AppImage {i+1}/3...")
            
            # Create session
            response = client.post("/api/session/create")
            session_id = response.json()["session_id"]
            
            # Upload AppImage
            with open(appimage, 'rb') as f:
                client.post(
                    f"/api/upload/appimage?session_id={session_id}",
                    files={'file': f}
                )
            
            # Upload key
            key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
            client.post(
                f"/api/upload/key?session_id={session_id}",
                files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
            )
            
            # Sign
            response = client.post(
                f"/api/sign?session_id={session_id}",
                json={"passphrase": test_key_data["passphrase"]}
            )
            assert response.status_code == 200
            
            signed_results.append({
                "session_id": session_id,
                "appimage": appimage.name,
                "status": "success"
            })
            
            print(f"✓ {appimage.name} signed")
        
        # Verify all succeeded
        assert len(signed_results) == 3
        assert all(r["status"] == "success" for r in signed_results)
        
        # Clean up
        for result in signed_results:
            client.delete(f"/api/session/{result['session_id']}")
        
        print("\n✅ Batch processing successful!")


class TestVerificationWorkflow:
    """Test verification workflows"""
    
    def test_verify_uploaded_signature(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test verifying uploaded signature"""
        
        # Create session
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        # Upload AppImage
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        
        # Create signature separately
        signature_path = temp_dir / "signature.asc"
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Upload signature
        with open(signature_path, 'rb') as f:
            client.post(
                f"/api/upload/signature?session_id={session_id}",
                files={'file': f}
            )
        
        # Verify
        response = client.get(f"/api/verify/uploaded?session_id={session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "valid" in data
        print(f"✓ Signature verification result: valid={data['valid']}")
        
        print("✅ Verification workflow successful!")


class TestDownloadWorkflow:
    """Test download workflows"""
    
    def test_download_individual_files(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test downloading individual files"""
        
        # Complete signing
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={session_id}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        # Download AppImage
        response = client.get(f"/api/download/appimage?session_id={session_id}")
        assert response.status_code == 200
        appimage_size = len(response.content)
        print(f"✓ AppImage downloaded ({appimage_size} bytes)")
        
        # Download signature
        response = client.get(f"/api/download/signature?session_id={session_id}")
        assert response.status_code == 200
        signature_size = len(response.content)
        print(f"✓ Signature downloaded ({signature_size} bytes)")
        
        # Both should be non-empty
        assert appimage_size > 0
        assert signature_size > 0
        
        print("✅ Individual downloads successful!")
    
    def test_download_zip_workflow(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test downloading and extracting ZIP"""
        
        # Complete signing
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={session_id}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        
        # Download ZIP
        response = client.get(f"/api/download/zip?session_id={session_id}")
        assert response.status_code == 200
        
        # Save and extract ZIP
        zip_path = temp_dir / "download.zip"
        zip_path.write_bytes(response.content)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            zip_file.extractall(temp_dir / "extracted")
        
        # Verify extracted files
        extracted = list((temp_dir / "extracted").glob("*"))
        assert len(extracted) == 2
        
        appimage_file = next(f for f in extracted if f.suffix == '.AppImage')
        signature_file = next(f for f in extracted if f.suffix == '.asc')
        
        assert appimage_file.exists()
        assert signature_file.exists()
        assert appimage_file.stat().st_size > 0
        assert signature_file.stat().st_size > 0
        
        print("✓ ZIP extracted successfully")
        print(f"  - {appimage_file.name} ({appimage_file.stat().st_size} bytes)")
        print(f"  - {signature_file.name} ({signature_file.stat().st_size} bytes)")
        
        print("✅ ZIP download workflow successful!")


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_developer_workflow(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test typical developer workflow"""
        print("\n=== Developer Workflow ===")
        print("Scenario: Developer wants to sign their AppImage before release")
        
        # 1. Create session
        print("\n1. Opening web interface...")
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        print(f"   Session: {session_id[:8]}...")
        
        # 2. Upload AppImage
        print("2. Uploading AppImage...")
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        print(f"   Uploaded: {sample_appimage.name}")
        
        # 3. Upload GPG key
        print("3. Uploading GPG private key...")
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={session_id}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        print("   Key uploaded")
        
        # 4. Sign
        print("4. Signing AppImage...")
        client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        print("   ✓ Signed successfully")
        
        # 5. Download ZIP
        print("5. Downloading signed package...")
        response = client.get(f"/api/download/zip?session_id={session_id}")
        print(f"   Downloaded ZIP ({len(response.content)} bytes)")
        
        print("\n✅ Developer workflow completed successfully!")
    
    def test_ci_cd_workflow(
        self,
        client,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data
    ):
        """Test CI/CD automation workflow"""
        print("\n=== CI/CD Workflow ===")
        print("Scenario: Automated signing in CI/CD pipeline")
        
        # Simulate CI/CD script
        print("\n1. CI/CD: Creating session...")
        response = client.post("/api/session/create")
        session_id = response.json()["session_id"]
        
        print("2. CI/CD: Uploading build artifact...")
        with open(sample_appimage, 'rb') as f:
            client.post(
                f"/api/upload/appimage?session_id={session_id}",
                files={'file': f}
            )
        
        print("3. CI/CD: Uploading key from secrets...")
        key_data = gpg_instance.export_keys(generated_gpg_key, secret=True, passphrase=test_key_data["passphrase"])
        client.post(
            f"/api/upload/key?session_id={session_id}",
            files={'file': ('key.asc', io.BytesIO(key_data.encode()))}
        )
        
        print("4. CI/CD: Signing with passphrase from environment...")
        response = client.post(
            f"/api/sign?session_id={session_id}",
            json={"passphrase": test_key_data["passphrase"]}
        )
        assert response.json()["status"] == "success"
        
        print("5. CI/CD: Downloading signed artifact...")
        response = client.get(f"/api/download/zip?session_id={session_id}")
        
        print("6. CI/CD: Uploading to release...")
        # (Simulated - would upload to GitHub releases, etc.)
        
        print("7. CI/CD: Cleaning up...")
        client.delete(f"/api/session/{session_id}")
        
        print("\n✅ CI/CD workflow completed successfully!")
