"""
Basic Re-Signer Tests
"""
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
