"""
Basic Key Manager Tests
"""
from src.key_manager import GPGKeyManager


class TestKeyManagerBasics:
    """Test basic key management"""

    def test_import_key(self, gpg_instance, generated_gpg_key, test_key_data, temp_dir):
        """Test importing a key"""
        manager = GPGKeyManager(gpg_home=gpg_instance.gnupghome)

        # Export key to file
        key_data = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )

        # Save to temporary file
        key_file = temp_dir / "test_key.asc"
        with open(key_file, 'w') as f:
            f.write(key_data)

        # Import should work
        result = manager.import_key(str(key_file))
        assert result is True

    def test_list_keys(self, gpg_instance, generated_gpg_key):
        """Test listing keys"""
        manager = GPGKeyManager(gpg_home=gpg_instance.gnupghome)

        keys = manager.list_keys()
        assert len(keys) > 0
