"""
PyTest Configuration and Fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import gnupg


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp(prefix="appimage_test_"))
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def gpg_home(temp_dir: Path) -> Generator[Path, None, None]:
    """Create temporary GPG home directory"""
    gpg_home = temp_dir / "gnupg"
    gpg_home.mkdir(parents=True, exist_ok=True)
    yield gpg_home


@pytest.fixture
def gpg_instance(gpg_home: Path) -> gnupg.GPG:
    """Create GPG instance with temporary home"""
    return gnupg.GPG(gnupghome=str(gpg_home))


@pytest.fixture
def test_key_data():
    """GPG test key data"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "passphrase": "test-passphrase-123",
        "key_type": "RSA",
        "key_length": 2048,
    }


@pytest.fixture
def generated_gpg_key(gpg_instance: gnupg.GPG, test_key_data: dict):
    """Generate a test GPG key"""
    key_input = gpg_instance.gen_key_input(
        name_real=test_key_data["name"],
        name_email=test_key_data["email"],
        passphrase=test_key_data["passphrase"],
        key_type=test_key_data["key_type"],
        key_length=test_key_data["key_length"],
    )
    key = gpg_instance.gen_key(key_input)
    return str(key)


@pytest.fixture
def sample_appimage(temp_dir: Path) -> Path:
    """Create a minimal valid AppImage Type 2 file"""
    appimage_path = temp_dir / "test-app.AppImage"

    with open(appimage_path, 'wb') as f:
        # ELF Header (simplified)
        f.write(b'\x7fELF')  # Magic bytes
        f.write(b'\x02' * 4)  # Padding to offset 8

        # AppImage Type 2 magic at offset 8
        f.write(b'AI\x02')

        # Add some dummy data
        f.write(b'\x00' * 1000)

    return appimage_path


@pytest.fixture
def invalid_file(temp_dir: Path) -> Path:
    """Create an invalid file (not an AppImage)"""
    file_path = temp_dir / "invalid.txt"
    with open(file_path, 'w') as f:
        f.write("This is not an AppImage")
    return file_path


@pytest.fixture
def large_file(temp_dir: Path) -> Path:
    """Create a large file for size validation testing"""
    file_path = temp_dir / "large.bin"
    size_mb = 600  # Larger than default limit (500 MB)

    with open(file_path, 'wb') as f:
        # Write in chunks to avoid memory issues
        chunk_size = 1024 * 1024  # 1 MB
        for _ in range(size_mb):
            f.write(b'\x00' * chunk_size)

    return file_path


@pytest.fixture
def mock_session_data():
    """Mock session data"""
    return {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "appimage_path": None,
        "key_path": None,
        "signed_appimage_path": None,
        "signature_path": None,
    }
