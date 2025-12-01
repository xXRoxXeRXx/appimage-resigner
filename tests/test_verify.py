"""
Basic Verification Tests
"""
import pytest
from src.verify import AppImageVerifier


class TestVerifyBasics:
    """Test basic verification"""

    def test_verify_signed_appimage(
        self,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test verifying a signed AppImage"""
        from src.resigner import AppImageResigner

        # First sign the AppImage
        resigner = AppImageResigner(gpg_home=gpg_instance.gnupghome)
        signed_path = temp_dir / "signed.AppImage"

        resigner.sign_appimage(
            str(sample_appimage),
            generated_gpg_key,
            str(signed_path),
            passphrase=test_key_data["passphrase"]
        )

        # Now verify it
        verifier = AppImageVerifier(gpg_home=gpg_instance.gnupghome)
        result = verifier.verify_signature(str(signed_path))

        assert result["valid"] is True

    def test_verify_unsigned_appimage(self, sample_appimage, gpg_instance):
        """Test verifying unsigned AppImage"""
        verifier = AppImageVerifier(gpg_home=gpg_instance.gnupghome)
        result = verifier.verify_signature(str(sample_appimage))

        # Should not be valid (no signature)
        assert result["valid"] is False
