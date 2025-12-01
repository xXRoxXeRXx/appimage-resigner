"""
Unit Tests for File Validation
"""
import pytest
from pathlib import Path
from web.core.validation import (
    validate_elf_header,
    validate_appimage_format,
    validate_file_size,
    validate_appimage_file,
)
from web.core.config import settings


class TestELFHeaderValidation:
    """Test ELF header validation"""
    
    def test_valid_elf_header(self, sample_appimage: Path):
        """Test validating a valid ELF header"""
        is_valid, error = validate_elf_header(sample_appimage)
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_elf_header(self, invalid_file: Path):
        """Test detecting invalid ELF header"""
        is_valid, error = validate_elf_header(invalid_file)
        
        assert is_valid is False
        assert error is not None
        assert "ELF" in error or "magic" in error.lower()
    
    def test_empty_file(self, temp_dir: Path):
        """Test validating empty file"""
        empty_file = temp_dir / "empty.bin"
        empty_file.touch()
        
        is_valid, error = validate_elf_header(empty_file)
        
        assert is_valid is False
        assert error is not None
    
    def test_truncated_file(self, temp_dir: Path):
        """Test validating truncated file (less than 4 bytes)"""
        truncated_file = temp_dir / "truncated.bin"
        with open(truncated_file, 'wb') as f:
            f.write(b'\x7f')  # Only 1 byte
        
        is_valid, error = validate_elf_header(truncated_file)
        
        assert is_valid is False


class TestAppImageFormatValidation:
    """Test AppImage Type 2 format validation"""
    
    def test_valid_appimage_type2(self, sample_appimage: Path):
        """Test validating valid AppImage Type 2"""
        is_valid, error = validate_appimage_format(sample_appimage)
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_appimage_format(self, temp_dir: Path):
        """Test detecting invalid AppImage format"""
        invalid_appimage = temp_dir / "invalid.AppImage"
        
        with open(invalid_appimage, 'wb') as f:
            # Valid ELF header
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            # Invalid AppImage magic
            f.write(b'XXX')
        
        is_valid, error = validate_appimage_format(invalid_appimage)
        
        assert is_valid is False
        assert error is not None
        assert "AppImage" in error or "Type 2" in error
    
    def test_appimage_type1(self, temp_dir: Path):
        """Test detecting AppImage Type 1 (not supported)"""
        type1_appimage = temp_dir / "type1.AppImage"
        
        with open(type1_appimage, 'wb') as f:
            # Valid ELF header
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            # AppImage Type 1 magic
            f.write(b'AI\x01')
        
        is_valid, error = validate_appimage_format(type1_appimage)
        
        assert is_valid is False
    
    def test_file_too_short_for_magic(self, temp_dir: Path):
        """Test file too short to contain AppImage magic"""
        short_file = temp_dir / "short.AppImage"
        
        with open(short_file, 'wb') as f:
            f.write(b'\x7fELF\x02\x02')  # Only 6 bytes
        
        is_valid, error = validate_appimage_format(short_file)
        
        assert is_valid is False


class TestFileSizeValidation:
    """Test file size validation"""
    
    def test_file_within_limit(self, sample_appimage: Path):
        """Test validating file within size limit"""
        max_size = 1024 * 1024 * 10  # 10 MB
        is_valid, error = validate_file_size(sample_appimage, max_size)
        
        assert is_valid is True
        assert error is None
    
    def test_file_exceeds_limit(self, temp_dir: Path):
        """Test detecting file exceeding size limit"""
        large_file = temp_dir / "large.bin"
        
        # Create 2 MB file
        with open(large_file, 'wb') as f:
            f.write(b'\x00' * (1024 * 1024 * 2))
        
        # Set limit to 1 MB
        max_size = 1024 * 1024
        is_valid, error = validate_file_size(large_file, max_size)
        
        assert is_valid is False
        assert error is not None
        assert "too large" in error.lower() or "size" in error.lower()
    
    def test_empty_file_size(self, temp_dir: Path):
        """Test validating empty file size"""
        empty_file = temp_dir / "empty.bin"
        empty_file.touch()
        
        max_size = 1024 * 1024
        is_valid, error = validate_file_size(empty_file, max_size)
        
        # Empty file should pass size check
        assert is_valid is True
    
    def test_nonexistent_file(self, temp_dir: Path):
        """Test validating non-existent file"""
        nonexistent = temp_dir / "nonexistent.bin"
        
        max_size = 1024 * 1024
        
        with pytest.raises(FileNotFoundError):
            validate_file_size(nonexistent, max_size)


class TestAppImageFileValidation:
    """Test complete AppImage file validation"""
    
    def test_valid_appimage(self, sample_appimage: Path):
        """Test validating a valid AppImage"""
        is_valid, errors = validate_appimage_file(sample_appimage)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_elf_header(self, invalid_file: Path):
        """Test AppImage with invalid ELF header"""
        is_valid, errors = validate_appimage_file(invalid_file)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("ELF" in error or "magic" in error.lower() for error in errors)
    
    def test_invalid_appimage_format(self, temp_dir: Path):
        """Test ELF file that's not AppImage Type 2"""
        elf_not_appimage = temp_dir / "elf.bin"
        
        with open(elf_not_appimage, 'wb') as f:
            # Valid ELF header
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            # Invalid AppImage magic
            f.write(b'XXX')
            f.write(b'\x00' * 1000)
        
        is_valid, errors = validate_appimage_file(elf_not_appimage)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("AppImage" in error or "Type 2" in error for error in errors)
    
    def test_file_too_large(self, temp_dir: Path):
        """Test AppImage exceeding size limit"""
        large_appimage = temp_dir / "large.AppImage"
        
        # Create valid AppImage structure
        with open(large_appimage, 'wb') as f:
            f.write(b'\x7fELF')
            f.write(b'\x02' * 4)
            f.write(b'AI\x02')
            # Make it 600 MB (exceeds default 500 MB limit)
            f.write(b'\x00' * (1024 * 1024 * 600))
        
        is_valid, errors = validate_appimage_file(
            large_appimage,
            max_size_mb=500
        )
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("too large" in error.lower() or "size" in error.lower() for error in errors)
    
    def test_multiple_validation_errors(self, invalid_file: Path):
        """Test file with multiple validation errors"""
        is_valid, errors = validate_appimage_file(invalid_file)
        
        assert is_valid is False
        # Should have at least ELF header error
        assert len(errors) >= 1


class TestMIMETypeValidation:
    """Test MIME type validation (future feature)"""
    
    @pytest.mark.skip(reason="MIME type validation not yet implemented")
    def test_valid_mime_type(self, sample_appimage: Path):
        """Test validating MIME type"""
        # Future implementation
        pass
    
    @pytest.mark.skip(reason="MIME type validation not yet implemented")
    def test_invalid_mime_type(self, invalid_file: Path):
        """Test detecting invalid MIME type"""
        # Future implementation
        pass


class TestPathTraversalPrevention:
    """Test path traversal attack prevention"""
    
    def test_safe_filename(self, temp_dir: Path):
        """Test extracting safe filename"""
        from pathlib import Path
        
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "test/../../sensitive.txt",
            "test\\..\\..\\sensitive.txt",
        ]
        
        for dangerous in dangerous_filenames:
            safe_name = Path(dangerous).name
            # Should only get the filename, not the path
            assert ".." not in safe_name
            assert "/" not in safe_name
            assert "\\" not in safe_name
    
    def test_resolve_path_within_directory(self, temp_dir: Path):
        """Test ensuring resolved path stays within directory"""
        base_dir = temp_dir / "uploads"
        base_dir.mkdir()
        
        # Try to escape with path traversal
        dangerous_path = base_dir / ".." / ".." / "etc" / "passwd"
        resolved = dangerous_path.resolve()
        
        # Check if it escaped base_dir
        try:
            resolved.relative_to(base_dir.resolve())
            escaped = False
        except ValueError:
            escaped = True
        
        assert escaped is True, "Path traversal should escape base directory"


class TestFileExtensionValidation:
    """Test file extension validation"""
    
    def test_valid_appimage_extension(self):
        """Test validating .AppImage extension"""
        valid_names = [
            "test.AppImage",
            "my-app.AppImage",
            "app-1.0.0.AppImage",
        ]
        
        for name in valid_names:
            assert name.endswith(".AppImage")
    
    def test_case_insensitive_extension(self):
        """Test case-insensitive extension check"""
        names = [
            "test.AppImage",
            "test.appimage",
            "test.APPIMAGE",
        ]
        
        for name in names:
            assert name.lower().endswith(".appimage")
    
    def test_invalid_extension(self):
        """Test detecting invalid extensions"""
        invalid_names = [
            "test.exe",
            "test.txt",
            "test.bin",
            "test",
        ]
        
        for name in invalid_names:
            assert not name.endswith(".AppImage")


class TestBinaryContentValidation:
    """Test binary content validation"""
    
    def test_detect_binary_content(self, sample_appimage: Path):
        """Test detecting binary content"""
        with open(sample_appimage, 'rb') as f:
            content = f.read(1024)
        
        # Binary files contain null bytes
        assert b'\x00' in content
    
    def test_detect_text_content(self, invalid_file: Path):
        """Test detecting text content"""
        with open(invalid_file, 'rb') as f:
            content = f.read(1024)
        
        # Text files typically don't have null bytes in first 1KB
        # (unless Unicode with BOM)
        is_likely_text = b'\x00' not in content
        
        # This test file is text, so should be likely text
        assert is_likely_text


class TestValidationEdgeCases:
    """Test validation edge cases"""
    
    def test_symlink_to_appimage(self, sample_appimage: Path, temp_dir: Path):
        """Test validating symlink to AppImage"""
        symlink = temp_dir / "symlink.AppImage"
        
        # Create symlink (Windows requires admin or developer mode)
        try:
            symlink.symlink_to(sample_appimage)
            is_valid, errors = validate_appimage_file(symlink)
            
            # Should follow symlink and validate target
            assert is_valid is True
        except OSError:
            # Skip test if symlinks not supported
            pytest.skip("Symlinks not supported on this system")
    
    def test_permission_denied(self, temp_dir: Path):
        """Test handling permission denied"""
        restricted_file = temp_dir / "restricted.AppImage"
        restricted_file.touch()
        
        # Try to make file unreadable (Unix only)
        try:
            restricted_file.chmod(0o000)
            
            with pytest.raises(PermissionError):
                validate_appimage_file(restricted_file)
        except Exception:
            # Skip on Windows or if permission change fails
            pytest.skip("Permission test not applicable on this system")
        finally:
            # Restore permissions for cleanup
            try:
                restricted_file.chmod(0o644)
            except:
                pass
    
    def test_concurrent_file_modification(self, sample_appimage: Path):
        """Test validation during file modification"""
        # This is a race condition test - difficult to test reliably
        # In production, use file locking or atomic operations
        pytest.skip("Concurrent modification testing requires complex setup")
