#!/usr/bin/env python3
"""
GPG Key Manager
Manages GPG keys for AppImage signing.
"""

import sys
import os
import argparse
import gnupg
from pathlib import Path


def find_gpg_binary():
    """Find GPG binary on the system."""
    # Common GPG locations on Windows
    gpg_paths = [
        r"C:\Program Files (x86)\GnuPG\bin\gpg.exe",
        r"C:\Program Files\GnuPG\bin\gpg.exe",
        r"C:\Program Files (x86)\Gpg4win\bin\gpg.exe",
        r"C:\Program Files\Gpg4win\bin\gpg.exe",
    ]
    
    # Check if gpg is in PATH
    import shutil
    gpg_in_path = shutil.which('gpg')
    if gpg_in_path:
        return gpg_in_path
    
    # Check common locations
    for path in gpg_paths:
        if os.path.exists(path):
            return path
    
    return None


class GPGKeyManager:
    """Class for managing GPG keys."""
    
    def __init__(self, gpg_home=None):
        """
        Initialize the key manager.
        
        Args:
            gpg_home (str): Path to GPG home directory. Defaults to ~/.gnupg
        """
        gpg_binary = find_gpg_binary()
        if gpg_binary:
            self.gpg = gnupg.GPG(gnupghome=gpg_home, gpgbinary=gpg_binary) if gpg_home else gnupg.GPG(gpgbinary=gpg_binary)
        else:
            self.gpg = gnupg.GPG(gnupghome=gpg_home) if gpg_home else gnupg.GPG()
    
    def generate_key(self, name, email, comment="", key_type="RSA", 
                    key_length=4096, expire_date=0, passphrase=None):
        """
        Generate a new GPG key pair.
        
        Args:
            name (str): Name for the key (e.g., "Company AppImage Signing")
            email (str): Email address for the key
            comment (str): Optional comment
            key_type (str): Key type (RSA, DSA, etc.)
            key_length (int): Key length in bits (2048, 4096)
            expire_date (int): Expiration in days (0 = never expires)
            passphrase (str): Passphrase to protect the private key
        
        Returns:
            dict: Key generation result with fingerprint
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
            print(f"\n✓ Key generated successfully!")
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
    
    def list_keys(self, secret=False):
        """
        List all GPG keys.
        
        Args:
            secret (bool): If True, list private keys; otherwise public keys
        
        Returns:
            list: List of key dictionaries
        """
        keys = self.gpg.list_keys(secret=secret)
        return keys
    
    def print_keys(self, secret=False):
        """
        Pretty print all GPG keys.
        
        Args:
            secret (bool): If True, list private keys; otherwise public keys
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
                print(f"Expires:      Never")
            
            print("-" * 80)
    
    def export_public_key(self, key_id, output_file):
        """
        Export a public key to a file (ASCII-armored).
        
        Args:
            key_id (str): Key ID or fingerprint to export
            output_file (str): Output file path
        
        Returns:
            bool: True if export was successful
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
    
    def export_private_key(self, key_id, output_file, passphrase=None):
        """
        Export a private key to a file (ASCII-armored).
        
        WARNING: Handle private keys with extreme care!
        
        Args:
            key_id (str): Key ID or fingerprint to export
            output_file (str): Output file path
            passphrase (str): Passphrase for the private key
        
        Returns:
            bool: True if export was successful
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
    
    def import_key(self, key_file):
        """
        Import a GPG key from a file.
        
        Args:
            key_file (str): Path to the key file
        
        Returns:
            bool: True if import was successful
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
    
    def generate_revocation_cert(self, key_id, output_file, passphrase=None):
        """
        Generate a revocation certificate for a key.
        
        Args:
            key_id (str): Key ID or fingerprint
            output_file (str): Output file path
            passphrase (str): Passphrase for the private key
        
        Returns:
            bool: True if generation was successful
        """
        # Note: python-gnupg doesn't directly support revocation cert generation
        # This would typically be done via command line: gpg --gen-revoke
        print("Note: Revocation certificate generation should be done via:")
        print(f"  gpg --output {output_file} --gen-revoke {key_id}")
        return False


def main():
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
