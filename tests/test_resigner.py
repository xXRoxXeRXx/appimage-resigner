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

        output_path = temp_dir / "unsigned.AppImage"
        result = resigner.remove_signature(
            str(sample_appimage),
            str(output_path)
        )

        assert result["success"] is True
        assert Path(output_path).exists()

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

        output_path = temp_dir / "signed.AppImage"
        result = resigner.sign_appimage(
            str(sample_appimage),
            generated_gpg_key,
            str(output_path),
            passphrase=test_key_data["passphrase"]
        )

        assert result["success"] is True
        assert Path(output_path).exists()

        # Check signature file created
        sig_path = Path(str(output_path) + ".asc")
        assert sig_path.exists()
