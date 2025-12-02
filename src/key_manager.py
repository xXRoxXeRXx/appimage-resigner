#!/usr/bin/env python3
"""
GPG Key Manager
Manages GPG keys for AppImage signing.
"""

import sys
import argparse
import gnupg  # type: ignore[import]
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.gpg_utils import create_gpg_instance


class GPGKeyManager:
    """Class for managing GPG keys."""

    gpg: gnupg.GPG

    def __init__(self, gpg_home: Optional[str] = None) -> None:
        """
        Initialize the key manager.

        Args:
            gpg_home: Path to GPG home directory. Defaults to ~/.gnupg
        """
        self.gpg = create_gpg_instance(gpg_home)

    def generate_key(
        self,
        name: str,
        email: str,
        comment: str = "",
        key_type: str = "RSA",
        key_length: int = 4096,
        expire_date: int = 0,
        passphrase: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a new GPG key pair.

        Args:
            name: Name for the key (e.g., "Company AppImage Signing")
            email: Email address for the key
            comment: Optional comment
            key_type: Key type (RSA, DSA, etc.)
            key_length: Key length in bits (2048, 4096)
            expire_date: Expiration in days (0 = never expires)
            passphrase: Passphrase to protect the private key

        Returns:
            Key generation result with fingerprint
        """
        input_data = self.gpg.gen_key_input(
            name_real=name,
            name_email=email,
            name_comment=comment,
            key_type=key_type,
            key_length=key_length,
            expire_date=expire_date,
            passphrase=passphrase
        )

        print("Generating GPG key pair...")
        print("This may take a while...")

        key = self.gpg.gen_key(input_data)

        if key:
            print("\n✓ Key generated successfully!")
            print(f"Fingerprint: {key}")
            return {
                'success': True,
                'fingerprint': str(key)
            }
        else:
            print("\n✗ Key generation failed!")
            return {
                'success': False,
                'error': 'Key generation failed'
            }

    def list_keys(self, secret: bool = False) -> List[Dict[str, Any]]:
        """
        List all GPG keys.

        Args:
            secret: If True, list private keys; otherwise public keys

        Returns:
            List of key dictionaries
        """
        keys = self.gpg.list_keys(secret=secret)
        return keys

    def print_keys(self, secret: bool = False) -> None:
        """
        Pretty print all GPG keys.

        Args:
            secret: If True, list private keys; otherwise public keys
        """
        keys = self.list_keys(secret=secret)

        key_type = "Private" if secret else "Public"
        print(f"\n{key_type} Keys:")
        print("=" * 80)

        if not keys:
            print(f"No {key_type.lower()} keys found.")
            return

        for key in keys:
            print(f"\nKey ID:       {key['keyid']}")
            print(f"Fingerprint:  {key['fingerprint']}")
            print(f"UIDs:         {', '.join(key['uids'])}")
            print(f"Length:       {key['length']} bits")
            print(f"Created:      {key['date']}")

            if key['expires']:
                print(f"Expires:      {key['expires']}")
            else:
                print("Expires:      Never")

            print("-" * 80)

    def export_public_key(self, key_id: str, output_file: str) -> bool:
        """
        Export a public key to a file (ASCII-armored).

        Args:
            key_id: Key ID or fingerprint to export
            output_file: Output file path

        Returns:
            True if export was successful
        """
        ascii_armored_key = self.gpg.export_keys(key_id)

        if ascii_armored_key:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                f.write(ascii_armored_key)
            print(f"✓ Public key exported to: {output_path}")
            return True
        else:
            print(f"✗ Failed to export public key for: {key_id}")
            return False

    def export_private_key(
        self,
        key_id: str,
        output_file: str,
        passphrase: Optional[str] = None
    ) -> bool:
        """
        Export a private key to a file (ASCII-armored).

        WARNING: Handle private keys with extreme care!

        Args:
            key_id: Key ID or fingerprint to export
            output_file: Output file path
            passphrase: Passphrase for the private key

        Returns:
            True if export was successful
        """
        ascii_armored_key = self.gpg.export_keys(
            key_id,
            secret=True,
            passphrase=passphrase
        )

        if ascii_armored_key:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                f.write(ascii_armored_key)
            print(f"✓ Private key exported to: {output_path}")
            print("⚠ WARNING: Keep this file secure!")
            return True
        else:
            print(f"✗ Failed to export private key for: {key_id}")
            return False

    def import_key(self, key_file: str) -> bool:
        """
        Import a GPG key from a file.

        Args:
            key_file: Path to the key file

        Returns:
            True if import was successful
        """
        key_path = Path(key_file)

        if not key_path.exists():
            print(f"✗ Key file not found: {key_path}")
            return False

        with open(key_path, 'r') as f:
            key_data = f.read()

        result = self.gpg.import_keys(key_data)

        if result.count > 0:
            print(f"✓ Successfully imported {result.count} key(s)")
            for fingerprint in result.fingerprints:
                print(f"  Fingerprint: {fingerprint}")
            return True
        else:
            print("✗ Failed to import key")
            return False

    def import_key_get_fingerprint(self, key_file: str) -> Optional[str]:
        """
        Import a GPG key from a file and return the fingerprint.

        Args:
            key_file: Path to the key file

        Returns:
            Fingerprint of the imported key if it's a private key, or None if import failed

        Raises:
            ValueError: If the key is a public key, not a private key
        """
        key_path = Path(key_file)

        if not key_path.exists():
            print(f"✗ Key file not found: {key_path}")
            return None

        # Try to read as text first (ASCII-armored), fallback to binary
        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                key_data = f.read()
            is_text = True
        except UnicodeDecodeError:
            # Binary format - read as bytes and let GPG handle it
            with open(key_path, 'rb') as f:
                key_data = f.read()
            is_text = False
            print("⚠ Key file is in binary format (not ASCII-armored)")

        # Check if this is a private key (only for text format)
        if is_text:
            if 'BEGIN PGP PRIVATE KEY BLOCK' not in key_data and 'BEGIN PRIVATE KEY' not in key_data:
                print("✗ This is not a private key!")
                print("  The uploaded key appears to be a PUBLIC key.")
                print("  You need to upload a PRIVATE key for signing.")
                raise ValueError("Not a private key: File must contain a private key (BEGIN PGP PRIVATE KEY BLOCK)")

        result = self.gpg.import_keys(key_data)

        # Debug: Log import result details
        print("GPG Import Result:")
        print(f"  Count: {result.count}")
        print(f"  Fingerprints: {result.fingerprints}")
        print(f"  Results: {result.results}")
        if hasattr(result, 'stderr'):
            print(f"  Stderr: {result.stderr}")

        if result.count > 0 and result.fingerprints:
            fingerprint = result.fingerprints[0]

            # Verify the key actually has a secret key
            secret_keys = self.gpg.list_keys(True)  # True = secret keys only
            print(f"  Available secret keys: {[k['fingerprint'] for k in secret_keys]}")

            has_secret = any(k['fingerprint'] == fingerprint for k in secret_keys)

            if not has_secret:
                print("✗ Key imported but no secret key found!")
                print(f"  Fingerprint: {fingerprint}")
                print("  This key cannot be used for signing.")
                raise ValueError(f"No secret key found for fingerprint {fingerprint}")

            print("✓ Successfully imported PRIVATE key")
            print(f"  Fingerprint: {fingerprint}")

            # Set ultimate trust for the imported key
            self._set_ultimate_trust(fingerprint)

            return fingerprint
        else:
            print("✗ Failed to import key")
            print(f"  Import stderr: {result.stderr if hasattr(result, 'stderr') else 'N/A'}")
            return None

    def _set_ultimate_trust(self, fingerprint: str) -> bool:
        """
        Set ultimate trust level for a key.

        This eliminates the "This key is not certified with a trusted signature!"
        warning when verifying signatures.

        Args:
            fingerprint: The key fingerprint

        Returns:
            True if trust was set successfully, False otherwise
        """
        try:
            import subprocess

            # Create trust input: fingerprint:6: (6 = ultimate trust)
            trust_input = f"{fingerprint}:6:\n"

            # Use gpg --import-ownertrust
            process = subprocess.Popen(
                ['gpg', '--import-ownertrust'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=trust_input)

            if process.returncode == 0:
                print(f"✓ Set ultimate trust for key {fingerprint[:16]}...")
                return True
            else:
                print(f"⚠ Could not set trust level: {stderr}")
                return False

        except Exception as e:
            print(f"⚠ Failed to set trust level: {e}")
            return False

    def import_key_from_string(self, key_content: str) -> Optional[str]:
        """
        Import a GPG key from a string and return the fingerprint.

        Args:
            key_content: The key content as a string (ASCII-armored)

        Returns:
            Fingerprint of the imported key if it's a private key, or None if import failed

        Raises:
            ValueError: If the key is a public key, not a private key
        """
        # Check if this is a private key
        if 'BEGIN PGP PRIVATE KEY BLOCK' not in key_content and 'BEGIN PRIVATE KEY' not in key_content:
            print("✗ This is not a private key!")
            print("  The uploaded key appears to be a PUBLIC key.")
            print("  You need to upload a PRIVATE key for signing.")
            raise ValueError("Not a private key: File must contain a private key (BEGIN PGP PRIVATE KEY BLOCK)")

        result = self.gpg.import_keys(key_content)

        # Debug: Log import result details
        print("GPG Import Result:")
        print(f"  Count: {result.count}")
        print(f"  Fingerprints: {result.fingerprints}")
        print(f"  Results: {result.results}")
        if hasattr(result, 'stderr'):
            print(f"  Stderr: {result.stderr}")

        if result.count > 0 and result.fingerprints:
            fingerprint = result.fingerprints[0]

            # Verify the key actually has a secret key
            secret_keys = self.gpg.list_keys(True)  # True = secret keys only
            print(f"  Available secret keys: {[k['fingerprint'] for k in secret_keys]}")

            has_secret = any(k['fingerprint'] == fingerprint for k in secret_keys)

            if not has_secret:
                print("✗ Key imported but no secret key found!")
                print(f"  Fingerprint: {fingerprint}")
                print("  This key cannot be used for signing.")
                raise ValueError(f"No secret key found for fingerprint {fingerprint}")

            print("✓ Successfully imported PRIVATE key")
            print(f"  Fingerprint: {fingerprint}")

            # Set ultimate trust for the imported key
            self._set_ultimate_trust(fingerprint)

            return fingerprint
        else:
            print("✗ Failed to import key")
            print(f"  Import stderr: {result.stderr if hasattr(result, 'stderr') else 'N/A'}")
            return None

    def generate_revocation_cert(
        self,
        key_id: str,
        output_file: str,
        passphrase: Optional[str] = None
    ) -> bool:
        """
        Generate a revocation certificate for a key.

        Args:
            key_id: Key ID or fingerprint
            output_file: Output file path
            passphrase: Passphrase for the private key

        Returns:
            True if generation was successful
        """
        # Note: python-gnupg doesn't directly support revocation cert generation
        # This would typically be done via command line: gpg --gen-revoke
        print("Note: Revocation certificate generation should be done via:")
        print(f"  gpg --output {output_file} --gen-revoke {key_id}")
        return False


def main() -> None:
    """Command-line interface for GPG key management."""
    parser = argparse.ArgumentParser(
        description="Manage GPG keys for AppImage signing"
    )

    parser.add_argument(
        "--gpg-home",
        help="Path to GPG home directory (default: ~/.gnupg)"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate key command
    gen_parser = subparsers.add_parser('generate', help='Generate a new key pair')
    gen_parser.add_argument('--name', required=True, help='Name for the key')
    gen_parser.add_argument('--email', required=True, help='Email for the key')
    gen_parser.add_argument('--comment', default='', help='Optional comment')
    gen_parser.add_argument('--passphrase', help='Passphrase for the key')
    gen_parser.add_argument('--no-expire', action='store_true',
                            help='Key never expires (recommended)')

    # List keys command
    list_parser = subparsers.add_parser('list', help='List GPG keys')
    list_parser.add_argument('--secret', action='store_true',
                             help='List private keys instead of public')

    # Export key command
    export_parser = subparsers.add_parser('export', help='Export a key')
    export_parser.add_argument('key_id', help='Key ID or fingerprint')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument('--secret', action='store_true',
                               help='Export private key (use with caution!)')
    export_parser.add_argument('--passphrase', help='Passphrase for private key')

    # Import key command
    import_parser = subparsers.add_parser('import', help='Import a key')
    import_parser.add_argument('key_file', help='Path to key file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize key manager
    manager = GPGKeyManager(gpg_home=args.gpg_home)

    # Execute command
    if args.command == 'generate':
        expire = 0 if args.no_expire else 730  # 2 years default
        result = manager.generate_key(
            name=args.name,
            email=args.email,
            comment=args.comment,
            expire_date=expire,
            passphrase=args.passphrase
        )
        sys.exit(0 if result['success'] else 1)

    elif args.command == 'list':
        manager.print_keys(secret=args.secret)

    elif args.command == 'export':
        if args.secret:
            success = manager.export_private_key(
                args.key_id,
                args.output,
                args.passphrase
            )
        else:
            success = manager.export_public_key(args.key_id, args.output)
        sys.exit(0 if success else 1)

    elif args.command == 'import':
        success = manager.import_key(args.key_file)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


# ============================================================================
# Key Storage & Management Methods (for Web Interface)
# ============================================================================

def list_all_keys_with_metadata() -> Dict[str, Any]:
    """
    List all GPG keys with detailed metadata for UI display.

    Returns:
        Dict with 'public_keys' and 'secret_keys' arrays
    """
    manager = GPGKeyManager()

    public_keys = manager.gpg.list_keys(False)  # Public keys
    secret_keys = manager.gpg.list_keys(True)   # Secret keys

    # Enhance keys with additional info
    def enhance_key(key: Dict[str, Any], is_secret: bool) -> Dict[str, Any]:
        """Add computed fields for UI."""
        import datetime

        # Parse expiry date
        expiry_date = None
        expiry_timestamp = key.get('expires')
        if expiry_timestamp and expiry_timestamp != '':
            try:
                expiry_date = datetime.datetime.fromtimestamp(int(expiry_timestamp)).isoformat()
            except (ValueError, TypeError):
                expiry_date = None

        # Extract name and email from first UID
        name = ""
        email = ""
        if key.get('uids'):
            uid = key['uids'][0]
            # Parse "Name (Comment) <email@example.com>"
            if '<' in uid and '>' in uid:
                parts = uid.split('<')
                name = parts[0].strip()
                email = parts[1].split('>')[0].strip()
            else:
                name = uid

        return {
            'fingerprint': key.get('fingerprint', ''),
            'keyid': key.get('keyid', ''),
            'type': key.get('type', ''),
            'length': key.get('length', 0),
            'algo': key.get('algo', ''),
            'trust': key.get('trust', 'unknown'),
            'ownertrust': key.get('ownertrust', ''),
            'uids': key.get('uids', []),
            'name': name,
            'email': email,
            'created': key.get('date', ''),
            'expires': expiry_date,
            'expired': key.get('expired', False),
            'disabled': key.get('disabled', False),
            'revoked': key.get('revoked', False),
            'is_secret': is_secret,
        }

    return {
        'public_keys': [enhance_key(k, False) for k in public_keys],
        'secret_keys': [enhance_key(k, True) for k in secret_keys],
        'total_public': len(public_keys),
        'total_secret': len(secret_keys),
    }


def get_key_by_fingerprint(fingerprint: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific key.

    Args:
        fingerprint: Key fingerprint

    Returns:
        Key metadata dict or None if not found
    """
    all_keys = list_all_keys_with_metadata()

    # Search in secret keys first
    for key in all_keys['secret_keys']:
        if key['fingerprint'] == fingerprint:
            return key

    # Then search in public keys
    for key in all_keys['public_keys']:
        if key['fingerprint'] == fingerprint:
            return key

    return None


def delete_key_by_fingerprint(fingerprint: str, delete_secret: bool = False) -> Dict[str, Any]:
    """
    Delete a key from the keyring.

    Args:
        fingerprint: Key fingerprint to delete
        delete_secret: If True, also delete secret key

    Returns:
        Dict with success status and message
    """
    manager = GPGKeyManager()

    try:
        # Delete secret key first if requested
        if delete_secret:
            result = manager.gpg.delete_keys(fingerprint, True, expect_passphrase=False)
            if not result.ok:
                return {
                    'success': False,
                    'error': f'Failed to delete secret key: {result.status}'
                }

        # Delete public key
        result = manager.gpg.delete_keys(fingerprint, False)
        if result.ok:
            return {
                'success': True,
                'message': f'Key {fingerprint[:16]}... deleted successfully'
            }
        else:
            return {
                'success': False,
                'error': f'Failed to delete public key: {result.status}'
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
