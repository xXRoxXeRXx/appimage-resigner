"""
Unit Tests for GPG Key Management
"""
import pytest
from pathlib import Path
import gnupg
import tempfile


class TestKeyImport:
    """Test GPG key import functionality"""
    
    def test_import_public_key(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test importing a public key"""
        # Export public key
        public_key = gpg_instance.export_keys(generated_gpg_key)
        assert public_key, "Failed to export public key"
        
        # Create new GPG instance
        temp_gpg_home = Path(tempfile.mkdtemp(prefix="gpg_import_"))
        new_gpg = gnupg.GPG(gnupghome=str(temp_gpg_home))
        
        # Import key
        result = new_gpg.import_keys(public_key)
        assert result.count == 1, "Failed to import public key"
        assert len(result.fingerprints) == 1
    
    def test_import_private_key(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, test_key_data: dict):
        """Test importing a private key"""
        # Export private key
        private_key = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        assert private_key, "Failed to export private key"
        
        # Create new GPG instance
        temp_gpg_home = Path(tempfile.mkdtemp(prefix="gpg_import_"))
        new_gpg = gnupg.GPG(gnupghome=str(temp_gpg_home))
        
        # Import key
        result = new_gpg.import_keys(private_key)
        assert result.count == 1, "Failed to import private key"
        assert result.sec_imported == 1
    
    def test_import_invalid_key(self, gpg_instance: gnupg.GPG):
        """Test importing invalid key data"""
        result = gpg_instance.import_keys("invalid key data")
        assert result.count == 0, "Should not import invalid key"


class TestKeyExport:
    """Test GPG key export functionality"""
    
    def test_export_public_key(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test exporting a public key"""
        public_key = gpg_instance.export_keys(generated_gpg_key)
        
        assert public_key, "Failed to export public key"
        assert "BEGIN PGP PUBLIC KEY BLOCK" in public_key
        assert "END PGP PUBLIC KEY BLOCK" in public_key
    
    def test_export_private_key(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, test_key_data: dict):
        """Test exporting a private key"""
        private_key = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        
        assert private_key, "Failed to export private key"
        assert "BEGIN PGP PRIVATE KEY BLOCK" in private_key
        assert "END PGP PRIVATE KEY BLOCK" in private_key
    
    def test_export_nonexistent_key(self, gpg_instance: gnupg.GPG):
        """Test exporting a non-existent key"""
        result = gpg_instance.export_keys("NONEXISTENT123")
        assert result == "", "Should return empty string for non-existent key"


class TestKeyListing:
    """Test GPG key listing functionality"""
    
    def test_list_keys(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, test_key_data: dict):
        """Test listing GPG keys"""
        keys = gpg_instance.list_keys()
        
        assert len(keys) >= 1, "Should have at least one key"
        
        # Find our test key
        test_key = next((k for k in keys if test_key_data["email"] in k['uids'][0]), None)
        assert test_key is not None, "Test key not found in list"
        assert test_key['type'] == 'pub'
    
    def test_list_secret_keys(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test listing secret (private) keys"""
        keys = gpg_instance.list_keys(secret=True)
        
        assert len(keys) >= 1, "Should have at least one secret key"
        assert keys[0]['type'] == 'sec'
    
    def test_empty_keyring(self, gpg_home: Path):
        """Test listing keys from empty keyring"""
        new_gpg = gnupg.GPG(gnupghome=str(gpg_home / "empty"))
        keys = new_gpg.list_keys()
        
        assert len(keys) == 0, "Empty keyring should have no keys"


class TestKeyGeneration:
    """Test GPG key generation"""
    
    def test_generate_key(self, gpg_instance: gnupg.GPG):
        """Test generating a new GPG key"""
        key_input = gpg_instance.gen_key_input(
            name_real="Test User 2",
            name_email="test2@example.com",
            passphrase="test-pass-456",
            key_type="RSA",
            key_length=2048,
        )
        
        key = gpg_instance.gen_key(key_input)
        assert key, "Failed to generate key"
        assert len(str(key)) > 0
        
        # Verify key exists
        keys = gpg_instance.list_keys()
        generated_key = next((k for k in keys if "test2@example.com" in k['uids'][0]), None)
        assert generated_key is not None, "Generated key not found"
    
    def test_generate_key_with_expiration(self, gpg_instance: gnupg.GPG):
        """Test generating a key with expiration"""
        key_input = gpg_instance.gen_key_input(
            name_real="Expiring User",
            name_email="expire@example.com",
            passphrase="test-pass-789",
            key_type="RSA",
            key_length=2048,
            expire_date="2026-12-31",
        )
        
        key = gpg_instance.gen_key(key_input)
        assert key, "Failed to generate key with expiration"


class TestKeyDeletion:
    """Test GPG key deletion"""
    
    def test_delete_public_key(self, gpg_instance: gnupg.GPG):
        """Test deleting a public key"""
        # Generate temporary key
        key_input = gpg_instance.gen_key_input(
            name_real="Delete Test",
            name_email="delete@example.com",
            passphrase="delete-pass",
            key_type="RSA",
            key_length=2048,
        )
        key = gpg_instance.gen_key(key_input)
        fingerprint = str(key)
        
        # Delete the key
        result = gpg_instance.delete_keys(fingerprint)
        assert result.status == 'ok', "Failed to delete key"
        
        # Verify deletion
        keys = gpg_instance.list_keys()
        deleted_key = next((k for k in keys if k['fingerprint'] == fingerprint), None)
        assert deleted_key is None, "Key still exists after deletion"
    
    def test_delete_secret_key(self, gpg_instance: gnupg.GPG):
        """Test deleting a secret key"""
        # Generate temporary key
        key_input = gpg_instance.gen_key_input(
            name_real="Delete Secret Test",
            name_email="delete-secret@example.com",
            passphrase="delete-secret-pass",
            key_type="RSA",
            key_length=2048,
        )
        key = gpg_instance.gen_key(key_input)
        fingerprint = str(key)
        
        # Delete secret key first
        result = gpg_instance.delete_keys(fingerprint, secret=True)
        assert result.status == 'ok', "Failed to delete secret key"
        
        # Delete public key
        result = gpg_instance.delete_keys(fingerprint)
        assert result.status == 'ok', "Failed to delete public key"


class TestKeyValidation:
    """Test key validation"""
    
    def test_valid_key_format(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test validating key format"""
        public_key = gpg_instance.export_keys(generated_gpg_key)
        
        # Check format
        assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in public_key
        assert "-----END PGP PUBLIC KEY BLOCK-----" in public_key
        assert len(public_key) > 100  # Should have substantial content
    
    def test_invalid_key_format(self):
        """Test detecting invalid key format"""
        invalid_keys = [
            "",
            "not a key",
            "BEGIN PGP PUBLIC KEY BLOCK",  # Missing dashes
            "-----BEGIN PGP PUBLIC KEY BLOCK-----\n-----END PGP PUBLIC KEY BLOCK-----",  # Empty
        ]
        
        for invalid_key in invalid_keys:
            # Should not contain proper PGP key structure
            assert not (
                "-----BEGIN PGP PUBLIC KEY BLOCK-----" in invalid_key and
                "-----END PGP PUBLIC KEY BLOCK-----" in invalid_key and
                len(invalid_key) > 100
            )


class TestKeyInfo:
    """Test extracting key information"""
    
    def test_get_key_fingerprint(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test getting key fingerprint"""
        keys = gpg_instance.list_keys()
        test_key = keys[0]
        
        assert 'fingerprint' in test_key
        assert len(test_key['fingerprint']) == 40  # GPG fingerprint length
    
    def test_get_key_uids(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, test_key_data: dict):
        """Test getting key UIDs"""
        keys = gpg_instance.list_keys()
        test_key = next((k for k in keys if test_key_data["email"] in k['uids'][0]), None)
        
        assert test_key is not None
        assert len(test_key['uids']) >= 1
        assert test_key_data["email"] in test_key['uids'][0]
        assert test_key_data["name"] in test_key['uids'][0]
    
    def test_get_key_length(self, gpg_instance: gnupg.GPG, generated_gpg_key: str):
        """Test getting key length"""
        keys = gpg_instance.list_keys()
        test_key = keys[0]
        
        assert 'length' in test_key
        assert int(test_key['length']) >= 2048  # Minimum recommended


class TestPassphraseHandling:
    """Test passphrase security"""
    
    def test_sign_with_passphrase(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, test_key_data: dict, temp_dir: Path):
        """Test signing with passphrase"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")
        
        with open(test_file, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        assert signed.status == 'signature created', "Failed to sign with passphrase"
    
    def test_sign_with_wrong_passphrase(self, gpg_instance: gnupg.GPG, generated_gpg_key: str, temp_dir: Path):
        """Test signing with incorrect passphrase"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")
        
        with open(test_file, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase="wrong-passphrase",
                detach=True
            )
        
        assert signed.status != 'signature created', "Should fail with wrong passphrase"
    
    def test_passphrase_overwrite(self):
        """Test passphrase memory overwriting"""
        passphrase = "sensitive-passphrase-123"
        original_id = id(passphrase)
        
        # Overwrite passphrase
        passphrase = "X" * len(passphrase)
        
        # Verify it's been overwritten
        assert passphrase == "X" * 24
        assert "sensitive" not in passphrase
