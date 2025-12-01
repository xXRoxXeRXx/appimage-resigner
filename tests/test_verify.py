"""
Basic Verification Tests
"""
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

        # Create a copy of the sample AppImage for this test
        signed_appimage = temp_dir / "signed_test.AppImage"
        import shutil
        shutil.copy2(sample_appimage, signed_appimage)

        # Sign the copy
        resigner = AppImageResigner(gpg_home=gpg_instance.gnupghome)
        resigner.sign_appimage(
            str(signed_appimage),
            key_id=generated_gpg_key,
            passphrase=test_key_data["passphrase"]
        )

        # Now verify it
        verifier = AppImageVerifier(gpg_home=gpg_instance.gnupghome)
        result = verifier.verify_signature(str(signed_appimage))

        assert result["valid"] is True

    def test_verify_unsigned_appimage(self, temp_dir, gpg_instance):
        """Test verifying unsigned AppImage"""
        # Create a fresh unsigned AppImage
        unsigned_appimage = temp_dir / "unsigned_test.AppImage"
        with open(unsigned_appimage, 'wb') as f:
            # ELF Header
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            # AppImage Type 2 magic
            f.write(b'AI\x02')
            # Dummy data
            f.write(b'\x00' * 1000)

        verifier = AppImageVerifier(gpg_home=gpg_instance.gnupghome)
        result = verifier.verify_signature(str(unsigned_appimage))

        # Should not be valid (no signature)
        assert result.get("valid") is False
