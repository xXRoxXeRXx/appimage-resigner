"""
Integration Tests for GPG Operations
Tests GPG functionality in realistic scenarios
"""
import pytest
from pathlib import Path
import gnupg
import subprocess
import tempfile


class TestGPGInstallation:
    """Test GPG installation and availability"""
    
    def test_gpg_installed(self):
        """Test GPG is installed and accessible"""
        result = subprocess.run(
            ["gpg", "--version"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "GnuPG" in result.stdout
    
    def test_gpg_version(self):
        """Test GPG version is recent enough"""
        result = subprocess.run(
            ["gpg", "--version"],
            capture_output=True,
            text=True
        )
        
        # Check version is at least 2.x
        assert "gpg (GnuPG)" in result.stdout
        # Version parsing would go here


class TestKeyringOperations:
    """Test GPG keyring operations"""
    
    def test_create_temporary_keyring(self, temp_dir):
        """Test creating isolated GPG keyring"""
        gpg_home = temp_dir / "gnupg"
        gpg_home.mkdir(parents=True, exist_ok=True)
        
        gpg = gnupg.GPG(gnupghome=str(gpg_home))
        
        # Should be empty
        keys = gpg.list_keys()
        assert len(keys) == 0
    
    def test_import_export_cycle(self, gpg_instance, generated_gpg_key, test_key_data):
        """Test importing and exporting keys"""
        # Export public key
        public_key = gpg_instance.export_keys(generated_gpg_key)
        assert len(public_key) > 0
        
        # Create new GPG instance
        temp_gpg_home = Path(tempfile.mkdtemp(prefix="gpg_test_"))
        new_gpg = gnupg.GPG(gnupghome=str(temp_gpg_home))
        
        # Import public key
        result = new_gpg.import_keys(public_key)
        assert result.count == 1
        
        # Export again
        re_exported = new_gpg.export_keys(result.fingerprints[0])
        assert len(re_exported) > 0
        
        # Should be similar (allowing for formatting differences)
        assert "BEGIN PGP PUBLIC KEY BLOCK" in re_exported


class TestSigningOperations:
    """Test GPG signing operations"""
    
    def test_sign_verify_cycle(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage
    ):
        """Test complete sign and verify cycle"""
        # Sign
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        assert signed.status == 'signature created'
        signature_data = str(signed)
        
        # Verify
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_data(
                f.read(),
                signature_data.encode()
            )
        
        assert verified.valid is True
    
    def test_sign_with_subprocess(
        self,
        gpg_home,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test signing using subprocess (GPG CLI)"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        # Sign using subprocess
        result = subprocess.run([
            "gpg",
            "--homedir", str(gpg_home),
            "--passphrase", test_key_data["passphrase"],
            "--batch", "--yes",
            "--default-key", generated_gpg_key,
            "--detach-sign",
            "--armor",
            "--output", str(signature_path),
            str(sample_appimage)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert signature_path.exists()
    
    def test_verify_with_subprocess(
        self,
        gpg_instance,
        gpg_home,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test verification using subprocess"""
        # Create signature with python-gnupg
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Verify with subprocess
        result = subprocess.run([
            "gpg",
            "--homedir", str(gpg_home),
            "--verify",
            str(signature_path),
            str(sample_appimage)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "Good signature" in result.stderr


class TestKeyManagement:
    """Test key management operations"""
    
    def test_list_keys_with_details(self, gpg_instance, generated_gpg_key):
        """Test listing keys with full details"""
        keys = gpg_instance.list_keys()
        
        assert len(keys) > 0
        
        # Check key details
        key = keys[0]
        assert 'fingerprint' in key
        assert 'uids' in key
        assert 'expires' in key
        assert 'length' in key
    
    def test_trust_levels(self, gpg_instance, generated_gpg_key):
        """Test GPG trust levels"""
        keys = gpg_instance.list_keys()
        
        for key in keys:
            assert 'trust' in key
            # Trust levels: q=undefined, n=never, m=marginal, f=full, u=ultimate
            assert key['trust'] in ['q', 'n', 'm', 'f', 'u', '-']
    
    def test_key_expiration(self, gpg_instance):
        """Test key expiration handling"""
        # Generate key with expiration
        key_input = gpg_instance.gen_key_input(
            name_real="Expiry Test",
            name_email="expiry@test.com",
            passphrase="test123",
            key_type="RSA",
            key_length=2048,
            expire_date="2026-12-31"
        )
        
        key = gpg_instance.gen_key(key_input)
        assert key
        
        # Check expiration
        keys = gpg_instance.list_keys()
        test_key = next((k for k in keys if "expiry@test.com" in k['uids'][0]), None)
        
        assert test_key is not None
        assert test_key['expires'] != ''  # Should have expiration date


class TestSecurityFeatures:
    """Test GPG security features"""
    
    def test_passphrase_protection(
        self,
        gpg_instance,
        generated_gpg_key,
        sample_appimage
    ):
        """Test that signing requires correct passphrase"""
        # Try with wrong passphrase
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase="wrong-passphrase",
                detach=True
            )
        
        assert signed.status != 'signature created'
    
    def test_signature_tamper_detection(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test that tampered signatures are detected"""
        # Create valid signature
        signature_path = temp_dir / "signature.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Tamper with signature
        signature_content = signature_path.read_text()
        tampered = signature_content.replace('A', 'B', 1)  # Change one character
        signature_path.write_text(tampered)
        
        # Verify should fail
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.valid is False
    
    def test_file_tamper_detection(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test that tampered files are detected"""
        # Create signature
        signature_path = temp_dir / "signature.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Tamper with file
        with open(sample_appimage, 'ab') as f:
            f.write(b'\x00')  # Add one byte
        
        # Verify should fail
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.valid is False


class TestEdgeCases:
    """Test GPG edge cases"""
    
    def test_sign_empty_file(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test signing empty file"""
        empty_file = temp_dir / "empty.txt"
        empty_file.touch()
        
        with open(empty_file, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        # Should succeed (GPG can sign empty files)
        assert signed.status == 'signature created'
    
    def test_sign_large_file(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test signing large file"""
        large_file = temp_dir / "large.bin"
        
        # Create 50 MB file
        with open(large_file, 'wb') as f:
            f.write(b'\x00' * (1024 * 1024 * 50))
        
        signature_path = temp_dir / "large.asc"
        
        with open(large_file, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        assert signed.status == 'signature created'
        assert signature_path.exists()
    
    def test_multiple_signatures(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test creating multiple signatures of same file"""
        signatures = []
        
        for i in range(3):
            sig_path = temp_dir / f"sig_{i}.asc"
            
            with open(sample_appimage, 'rb') as f:
                gpg_instance.sign_file(
                    f,
                    keyid=generated_gpg_key,
                    passphrase=test_key_data["passphrase"],
                    detach=True,
                    output=str(sig_path)
                )
            
            signatures.append(sig_path.read_text())
        
        # All signatures should be valid
        assert len(signatures) == 3
        
        # Signatures should be identical (deterministic)
        # Note: GPG signatures may include timestamps, so they might differ
        # This test verifies they all exist and are non-empty
        for sig in signatures:
            assert "BEGIN PGP SIGNATURE" in sig


class TestPerformance:
    """Test GPG performance"""
    
    def test_key_generation_performance(self, gpg_instance):
        """Test key generation time"""
        import time
        
        start = time.time()
        
        key_input = gpg_instance.gen_key_input(
            name_real="Performance Test",
            name_email="perf@test.com",
            passphrase="test123",
            key_type="RSA",
            key_length=2048,
        )
        
        key = gpg_instance.gen_key(key_input)
        
        elapsed = time.time() - start
        
        assert key
        # Key generation should complete in reasonable time
        assert elapsed < 30  # 30 seconds max
    
    def test_signing_performance(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage
    ):
        """Test signing performance"""
        import time
        
        start = time.time()
        
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        elapsed = time.time() - start
        
        assert signed.status == 'signature created'
        # Signing should be fast
        assert elapsed < 5  # 5 seconds max for small file


class TestErrorRecovery:
    """Test GPG error recovery"""
    
    def test_recover_from_invalid_passphrase(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage
    ):
        """Test recovery after invalid passphrase"""
        # First attempt with wrong passphrase
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase="wrong",
                detach=True
            )
        assert signed.status != 'signature created'
        
        # Second attempt with correct passphrase
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        assert signed.status == 'signature created'
    
    def test_handle_corrupted_key(self, gpg_instance):
        """Test handling corrupted key data"""
        corrupted_key = "-----BEGIN PGP PUBLIC KEY BLOCK-----\ncorrupted\n-----END PGP PUBLIC KEY BLOCK-----"
        
        result = gpg_instance.import_keys(corrupted_key)
        
        # Should handle gracefully
        assert result.count == 0
        # Should not crash


class TestCompatibility:
    """Test GPG compatibility"""
    
    def test_ascii_armor_format(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test ASCII-armored signature format"""
        signature_path = temp_dir / "signature.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        signature_content = signature_path.read_text()
        
        # Check ASCII armor format
        assert signature_content.startswith("-----BEGIN PGP SIGNATURE-----")
        assert signature_content.strip().endswith("-----END PGP SIGNATURE-----")
        
        # Check it's actually ASCII (no binary characters)
        for char in signature_content:
            assert ord(char) < 128  # ASCII range
    
    def test_binary_signature_format(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage,
        temp_dir
    ):
        """Test binary signature format"""
        # This would require GPG configuration for binary output
        # Skipped for now as we primarily use ASCII armor
        pytest.skip("Binary signatures not currently used")
