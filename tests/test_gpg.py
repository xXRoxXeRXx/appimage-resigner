"""
Basic GPG Functionality Tests
"""
import pytest
import subprocess


class TestGPGBasics:
    \"\"\"Test basic GPG functionality\"\"\"
    
    def test_gpg_installed(self):
        \"\"\"Test GPG is installed\"\"\"
        result = subprocess.run(
            ["gpg", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "GnuPG" in result.stdout
    
    def test_sign_and_verify(
        self,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        sample_appimage
    ):
        \"\"\"Test basic sign and verify cycle\"\"\"
        # Sign file
        with open(sample_appimage, 'rb') as f:
            signed = gpg_instance.sign_file(
                f,
                keyid=generated_gpg_key,
                passphrase=test_key_data["passphrase"],
                detach=True
            )
        
        assert signed.status == 'signature created'
        
        # Verify signature
        with open(sample_appimage, 'rb') as f:
            verified = gpg_instance.verify_data(
                str(signed).encode(),
                f.read()
            )
        
        assert verified.valid
