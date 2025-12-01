"""
Basic Key Manager Tests
"""
import pytest
from src.key_manager import KeyManager


class TestKeyManagerBasics:
    """Test basic key management"""
    
    def test_import_key(self, gpg_instance, generated_gpg_key, test_key_data):
        """Test importing a key"""
        manager = KeyManager(gpg_home=gpg_instance.gnupghome)
        
        # Export key
        key_data = gpg_instance.export_keys(
            generated_gpg_key,
            secret=True,
            passphrase=test_key_data["passphrase"]
        )
        
        # Import should work
        result = manager.import_key(key_data)
        assert result["success"] is True
    
    def test_list_keys(self, gpg_instance, generated_gpg_key):
        """Test listing keys"""
        manager = KeyManager(gpg_home=gpg_instance.gnupghome)
        
        keys = manager.list_keys()
        assert len(keys["secret_keys"]) > 0 or len(keys["public_keys"]) > 0
