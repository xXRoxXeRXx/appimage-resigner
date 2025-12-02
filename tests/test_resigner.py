"""
Basic Re-Signer Tests
"""
import pytest
from pathlib import Path
from src.resigner import AppImageResigner


class TestResigerBasics:
    """Test basic re-signing functionality"""

    def test_remove_signature(self, sample_appimage, temp_dir):
        """Test signature removal"""
        resigner = AppImageResigner()

        result = resigner.remove_signature(str(sample_appimage))
        assert result is True

    def test_sign_appimage(
        self,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test AppImage signing"""
        resigner = AppImageResigner(gpg_home=gpg_instance.gnupghome)

        output_path = temp_dir / "signed.AppImage.asc"
        result = resigner.sign_appimage(
            str(sample_appimage),
            key_id=generated_gpg_key,
            passphrase=test_key_data["passphrase"],
            output_path=str(output_path)
        )

        assert result is True
        assert Path(output_path).exists()


class TestResignerEdgeCases:
    """Test edge cases and error handling"""

    def test_remove_signature_nonexistent_file(self, temp_dir):
        """Test signature removal on nonexistent file"""
        resigner = AppImageResigner()
        nonexistent = temp_dir / "nonexistent.AppImage"

        result = resigner.remove_signature(str(nonexistent))
        assert result is False

    def test_sign_nonexistent_file(self, temp_dir):
        """Test signing a nonexistent file"""
        resigner = AppImageResigner()
        nonexistent = temp_dir / "nonexistent.AppImage"

        result = resigner.sign_appimage(str(nonexistent))
        assert result is False

    def test_sign_with_invalid_key(self, sample_appimage, temp_dir):
        """Test signing with a key that doesn't exist"""
        resigner = AppImageResigner()

        result = resigner.sign_appimage(
            str(sample_appimage),
            key_id="NONEXISTENT_KEY_ID"
        )
        # This should fail because key doesn't exist
        assert result is False

    def test_resign_workflow(
        self,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test the full resign workflow"""
        resigner = AppImageResigner(gpg_home=gpg_instance.gnupghome)

        result = resigner.resign_appimage(
            str(sample_appimage),
            key_id=generated_gpg_key,
            passphrase=test_key_data["passphrase"]
        )

        assert result is True
        # Check that signature file was created
        asc_file = Path(str(sample_appimage) + ".asc")
        assert asc_file.exists()

    def test_embed_signature(
        self,
        sample_appimage,
        gpg_instance,
        generated_gpg_key,
        test_key_data,
        temp_dir
    ):
        """Test embedding signature in AppImage"""
        resigner = AppImageResigner(gpg_home=gpg_instance.gnupghome)

        result = resigner.sign_appimage(
            str(sample_appimage),
            key_id=generated_gpg_key,
            passphrase=test_key_data["passphrase"],
            embed_signature=True
        )

        assert result is True

        # Check that signature is embedded
        with open(sample_appimage, 'rb') as f:
            content = f.read()
            assert b'-----BEGIN PGP SIGNATURE-----' in content
