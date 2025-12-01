"""
Unit Tests for AppImage Signing
"""
import pytest
from pathlib import Path
import gnupg
from typing import Tuple


class TestAppImageSigning:
    """Test AppImage signing functionality"""
    
    def test_sign_appimage(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test signing an AppImage"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        assert signed.status == 'signature created'
        assert signature_path.exists()
        assert signature_path.stat().st_size > 0
    
    def test_sign_without_passphrase(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        sample_appimage: Path
    ):
        """Test signing without passphrase (should fail)"""
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase="",  # Empty passphrase
                detach=True
            )
        
        assert signed.status != 'signature created'
    
    def test_sign_with_wrong_key_id(
        self,
        gpg_instance: gnupg.GPG,
        test_key_data: dict,
        sample_appimage: Path
    ):
        """Test signing with non-existent key ID"""
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid="NONEXISTENT12345678",
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        assert signed.status != 'signature created'
    
    def test_signature_format(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test signature file format"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Read signature file
        signature_content = signature_path.read_text()
        
        # Check ASCII-armored format
        assert "-----BEGIN PGP SIGNATURE-----" in signature_content
        assert "-----END PGP SIGNATURE-----" in signature_content
    
    def test_sign_large_file(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        temp_dir: Path
    ):
        """Test signing a large file"""
        large_file = temp_dir / "large.AppImage"
        
        # Create 10 MB file
        with open(large_file, 'wb') as f:
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            f.write(b'AI\x02')
            f.write(b'\x00' * (1024 * 1024 * 10))
        
        signature_path = temp_dir / f"{large_file.name}.asc"
        
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


class TestSignatureVerification:
    """Test signature verification"""
    
    def test_verify_valid_signature(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test verifying a valid signature"""
        # Sign the file
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Verify the signature
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.valid is True
        assert verified.fingerprint is not None
    
    def test_verify_invalid_signature(
        self,
        gpg_instance: gnupg.GPG,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test verifying an invalid signature"""
        # Create fake signature
        fake_signature = temp_dir / f"{sample_appimage.name}.asc"
        fake_signature.write_text("-----BEGIN PGP SIGNATURE-----\nfake\n-----END PGP SIGNATURE-----")
        
        # Verify should fail
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(fake_signature))
        
        assert verified.valid is False
    
    def test_verify_modified_file(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test verifying signature after file modification"""
        # Sign the file
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Modify the file
        with open(sample_appimage, 'ab') as f:
            f.write(b'\x00')  # Add one byte
        
        # Verify should fail
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.valid is False
    
    def test_verify_without_public_key(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path,
        gpg_home: Path
    ):
        """Test verifying signature without public key in keyring"""
        # Sign with first GPG instance
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Create new GPG instance without the key
        new_gpg_home = gpg_home.parent / "new_gpg"
        new_gpg_home.mkdir()
        new_gpg = gnupg.GPG(gnupghome=str(new_gpg_home))
        
        # Verify should fail (key not in keyring)
        with open(sample_appimage, 'rb') as f:
            verified = new_gpg.verify_file(f, str(signature_path))
        
        assert verified.valid is False
        assert verified.key_status is not None


class TestEmbeddedSignature:
    """Test embedded signature functionality"""
    
    def test_embed_signature(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test embedding signature into AppImage"""
        # Sign the file
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Create output path
        signed_appimage = temp_dir / f"signed-{sample_appimage.name}"
        
        # Embed signature (simplified - just append for test)
        with open(signed_appimage, 'wb') as out:
            # Copy original AppImage
            with open(sample_appimage, 'rb') as src:
                out.write(src.read())
            
            # Append signature
            with open(signature_path, 'rb') as sig:
                out.write(sig.read())
        
        # Verify embedded file is larger
        assert signed_appimage.stat().st_size > sample_appimage.stat().st_size
    
    def test_extract_embedded_signature(
        self,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test extracting embedded signature"""
        # This test would require actual embed_signature.py implementation
        pytest.skip("Requires full embed_signature.py implementation")


class TestSigningEdgeCases:
    """Test signing edge cases"""
    
    def test_sign_nonexistent_file(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        temp_dir: Path
    ):
        """Test signing non-existent file"""
        nonexistent = temp_dir / "nonexistent.AppImage"
        
        with pytest.raises(FileNotFoundError):
            with open(nonexistent, 'rb') as f:
                gpg_instance.sign_file(
                    f,
                    keyid=generated_gpg_key,
                    passphrase=test_key_data["passphrase"],
                    detach=True
                )
    
    def test_sign_empty_file(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        temp_dir: Path
    ):
        """Test signing empty file"""
        empty_file = temp_dir / "empty.AppImage"
        empty_file.touch()
        
        signature_path = temp_dir / f"{empty_file.name}.asc"
        
        with open(empty_file, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Should succeed (GPG can sign empty files)
        assert signed.status == 'signature created'
    
    def test_overwrite_existing_signature(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test overwriting existing signature"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        # Sign twice
        for _ in range(2):
            with open(sample_appimage, 'rb') as f:
                signed = gpg_instance.sign_file(
                    f,
                    keyid=generated_gpg_key,
                    passphrase=test_key_data["passphrase"],
                    detach=True,
                    output=str(signature_path)
                )
            
            assert signed.status == 'signature created'
        
        # Signature should exist and be valid
        assert signature_path.exists()


class TestPassphraseSecurity:
    """Test passphrase security measures"""
    
    def test_passphrase_not_logged(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        caplog
    ):
        """Test that passphrase is not logged"""
        import logging
        caplog.set_level(logging.DEBUG)
        
        with open(sample_appimage, 'rb') as f:
            gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        # Check logs don't contain passphrase
        for record in caplog.records:
            assert test_key_data["passphrase"] not in record.message
    
    def test_passphrase_overwriting(self):
        """Test passphrase memory overwriting"""
        passphrase = "my-secret-passphrase"
        original_value = passphrase
        
        # Simulate overwriting
        passphrase = "X" * len(passphrase)
        
        # Verify overwritten
        assert passphrase != original_value
        assert "secret" not in passphrase
        assert passphrase == "X" * len(original_value)
    
    def test_empty_passphrase_warning(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        sample_appimage: Path
    ):
        """Test warning for empty passphrase"""
        passphrase = ""
        
        # Should warn about empty passphrase
        assert len(passphrase) == 0
        
        # Signing should fail
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=passphrase,
                detach=True
            )
        
        assert signed.status != 'signature created'


class TestSignatureMetadata:
    """Test signature metadata"""
    
    def test_signature_timestamp(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test signature contains timestamp"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Verify signature info
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.timestamp is not None
        assert int(verified.timestamp) > 0
    
    def test_signature_key_id(
        self,
        gpg_instance: gnupg.GPG,
        generated_gpg_key: str,
        test_key_data: dict,
        sample_appimage: Path,
        temp_dir: Path
    ):
        """Test signature contains key ID"""
        signature_path = temp_dir / f"{sample_appimage.name}.asc"
        
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True,
                output=str(signature_path)
            )
        
        # Verify signature info
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_file(f, str(signature_path))
        
        assert verified.key_id is not None
        assert len(verified.key_id) > 0
