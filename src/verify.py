#!/usr/bin/env python3
"""
AppImage Signature Verifier
Verifies GPG signatures of AppImage files.
"""

import sys
import os
import argparse
import gnupg
import shutil
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
    gpg_in_path = shutil.which('gpg')
    if gpg_in_path:
        return gpg_in_path
    
    # Check common locations
    for path in gpg_paths:
        if os.path.exists(path):
            return path
    
    return None


class AppImageVerifier:
    """Class for verifying AppImage signatures."""
    
    def __init__(self, gpg_home=None):
        """
        Initialize the verifier.
        
        Args:
            gpg_home (str): Path to GPG home directory. Defaults to ~/.gnupg
        """
        gpg_binary = find_gpg_binary()
        if gpg_binary:
            self.gpg = gnupg.GPG(gnupghome=gpg_home, gpgbinary=gpg_binary) if gpg_home else gnupg.GPG(gpgbinary=gpg_binary)
        else:
            self.gpg = gnupg.GPG(gnupghome=gpg_home) if gpg_home else gnupg.GPG()
    
    def get_signature_info(self, appimage_path):
        """
        Get information about a signature without verifying it.
        Just checks if a signature exists and extracts basic info.
        
        Args:
            appimage_path (str): Path to the AppImage file
            
        Returns:
            dict: Signature information (has_signature, type, signature_data)
        """
        appimage_path = Path(appimage_path)
        
        if not appimage_path.exists():
            return {
                'has_signature': False,
                'error': f"AppImage file not found: {appimage_path}"
            }
        
        try:
            # Check for embedded signature
            with open(appimage_path, 'rb') as f:
                content = f.read()
                
                if b'-----BEGIN PGP SIGNATURE-----' in content:
                    sig_start = content.rfind(b'-----BEGIN PGP SIGNATURE-----')
                    sig_data = content[sig_start:].decode('utf-8', errors='ignore')
                    
                    # Extract just the first few lines for display
                    sig_lines = sig_data.split('\n')
                    sig_preview = '\n'.join(sig_lines[:10])
                    
                    return {
                        'has_signature': True,
                        'type': 'embedded',
                        'signature_data': sig_preview + '\n...' if len(sig_lines) > 10 else sig_data,
                        'size': len(sig_data)
                    }
            
            # Check for external .asc file
            asc_path = Path(str(appimage_path) + ".asc")
            if asc_path.exists():
                with open(asc_path, 'r') as f:
                    sig_data = f.read()
                    sig_lines = sig_data.split('\n')
                    sig_preview = '\n'.join(sig_lines[:10])
                    
                    return {
                        'has_signature': True,
                        'type': 'external',
                        'signature_data': sig_preview + '\n...' if len(sig_lines) > 10 else sig_data,
                        'size': len(sig_data)
                    }
            
            return {
                'has_signature': False,
                'error': 'No signature found (neither embedded nor external .asc file)'
            }
            
        except Exception as e:
            return {
                'has_signature': False,
                'error': f"Error reading signature: {str(e)}"
            }
    
    def extract_embedded_signature(self, appimage_path):
        """
        Extract embedded signature from AppImage file.
        AppImages can have their signature embedded at the end of the file.
        
        Args:
            appimage_path (str): Path to the AppImage file
            
        Returns:
            dict: Signature information or None if no signature found
        """
        appimage_path = Path(appimage_path)
        
        if not appimage_path.exists():
            return None
        
        try:
            # Read the entire file to look for embedded signature
            with open(appimage_path, 'rb') as f:
                content = f.read()
                
                # Look for GPG signature markers
                if b'-----BEGIN PGP SIGNATURE-----' in content:
                    # Find where signature starts
                    sig_start = content.rfind(b'-----BEGIN PGP SIGNATURE-----')
                    
                    print(f"🔍 Found embedded signature at position {sig_start}")
                    
                    # The signature might be preceded by newline(s) that weren't part of the signed data
                    # We need to find where the actual signed data ends
                    data_end = sig_start
                    # Skip backwards over any whitespace/newlines before the signature
                    while data_end > 0 and content[data_end - 1:data_end] in (b'\n', b'\r', b' ', b'\t'):
                        data_end -= 1
                    
                    # Extract signature block
                    sig_data = content[sig_start:].decode('utf-8', errors='ignore')
                    
                    # Get the data before the signature (this is what was signed)
                    data_before_sig = content[:data_end]
                    
                    print(f"🔍 Data size before signature: {len(data_before_sig)} bytes (trimmed from {sig_start})")
                    print(f"🔍 Signature size: {len(sig_data)} bytes")
                    
                    # Save to temporary files for verification
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.data') as data_file:
                        data_file.write(data_before_sig)
                        data_path = data_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.asc') as sig_file:
                        sig_file.write(sig_data)
                        sig_path = sig_file.name
                    
                    print(f"🔍 Temp data file: {data_path}")
                    print(f"🔍 Temp sig file: {sig_path}")
                    
                    try:
                        # Verify the signature against the data
                        with open(sig_path, 'rb') as sf:
                            verified = self.gpg.verify_file(sf, data_path)
                        
                        print(f"🔍 GPG verify result: valid={verified.valid}, status={verified.status}")
                        print(f"🔍 Key ID: {verified.key_id}")
                        print(f"🔍 Username: {verified.username}")
                        print(f"🔍 Trust level: {getattr(verified, 'trust_level', 'N/A')}")
                        print(f"🔍 Trust text: {getattr(verified, 'trust_text', 'N/A')}")
                        if hasattr(verified, 'stderr') and verified.stderr:
                            print(f"🔍 GPG stderr: {verified.stderr}")
                        
                        # List available keys for debugging
                        public_keys = self.gpg.list_keys()
                        print(f"🔍 Available public keys in keyring: {len(public_keys)}")
                        for key in public_keys:
                            print(f"   - Key ID: {key['keyid']}, UID: {key['uids'][0] if key['uids'] else 'N/A'}")
                        
                        return {
                            'has_signature': True,
                            'valid': verified.valid if verified else False,
                            'key_id': verified.key_id if verified else None,
                            'username': verified.username if verified and verified.username else 'Unknown',
                            'fingerprint': verified.fingerprint if verified and verified.fingerprint else None,
                            'timestamp': verified.sig_timestamp if verified and hasattr(verified, 'sig_timestamp') else None,
                            'trust_level': verified.trust_text if verified and hasattr(verified, 'trust_text') else None,
                            'signature_data': sig_data[:200] + '...' if len(sig_data) > 200 else sig_data,
                            'embedded': True,
                            'status': verified.status if verified else 'unknown'
                        }
                    finally:
                        # Clean up temp files
                        try:
                            os.unlink(data_path)
                            os.unlink(sig_path)
                        except:
                            pass
                else:
                    print(f"🔍 No embedded signature found in {appimage_path}")
                    return {
                        'has_signature': False,
                        'error': 'No embedded signature found in AppImage'
                    }
                    
        except Exception as e:
            return {
                'has_signature': False,
                'error': f"Could not extract signature: {str(e)}"
            }
    
    def verify_signature(self, appimage_path, signature_path=None):
        """
        Verify the GPG signature of an AppImage.
        
        Args:
            appimage_path (str): Path to the AppImage file
            signature_path (str): Path to the .asc signature file.
                                If None, tries embedded signature first, then looks for .asc
        
        Returns:
            dict: Verification result with keys:
                - valid (bool): True if signature is valid
                - key_id (str): ID of the signing key
                - username (str): Name associated with the key
                - timestamp (str): Signature timestamp
                - fingerprint (str): Key fingerprint
        """
        appimage_path = Path(appimage_path)
        
        if not appimage_path.exists():
            return {
                'valid': False,
                'error': f"AppImage file not found: {appimage_path}"
            }
        
        # If no external signature specified, try embedded signature first
        if signature_path is None:
            embedded = self.extract_embedded_signature(appimage_path)
            if embedded and embedded.get('has_signature'):
                return embedded
            
            # Fall back to external .asc file
            signature_path = Path(str(appimage_path) + ".asc")
        else:
            signature_path = Path(signature_path)
        
        if not signature_path.exists():
            return {
                'valid': False,
                'has_signature': False,
                'error': f"No signature found (neither embedded nor external .asc file)"
            }
        
        try:
            # Verify using file paths (more efficient for large files)
            with open(signature_path, 'rb') as sig_file:
                verified = self.gpg.verify_file(sig_file, str(appimage_path))
            
            if verified.valid:
                return {
                    'valid': True,
                    'key_id': verified.key_id,
                    'username': verified.username or 'Unknown',
                    'timestamp': verified.sig_timestamp,
                    'fingerprint': verified.fingerprint or 'N/A',
                    'trust_level': verified.trust_text or 'Unknown'
                }
            else:
                # Even if not valid, try to extract some info
                return {
                    'valid': False,
                    'error': f"Invalid signature: {verified.status or 'Unknown status'}",
                    'key_id': verified.key_id or 'N/A',
                    'stderr': getattr(verified, 'stderr', '')
                }
                
        except FileNotFoundError as e:
            return {
                'valid': False,
                'error': f"File not found: {str(e)}"
            }
        except Exception as e:
            import traceback
            return {
                'valid': False,
                'error': f"Verification error: {str(e)}",
                'traceback': traceback.format_exc()
            }
    
    def print_verification_result(self, result, appimage_path):
        """
        Pretty print verification results.
        
        Args:
            result (dict): Verification result from verify_signature()
            appimage_path (str): Path to the AppImage file
        """
        print("=" * 60)
        print(f"AppImage Signature Verification")
        print("=" * 60)
        print(f"File: {appimage_path}")
        print()
        
        if result['valid']:
            print("✓ SIGNATURE VALID")
            print()
            print(f"Signed by:    {result.get('username', 'Unknown')}")
            print(f"Key ID:       {result['key_id']}")
            print(f"Fingerprint:  {result.get('fingerprint', 'N/A')}")
            print(f"Trust Level:  {result.get('trust_level', 'Unknown')}")
            
            if result.get('timestamp'):
                from datetime import datetime
                ts = datetime.fromtimestamp(int(result['timestamp']))
                print(f"Signed on:    {ts.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("✗ SIGNATURE INVALID")
            print()
            print(f"Error: {result.get('error', 'Unknown error')}")
            if 'stderr' in result:
                print(f"Details: {result['stderr']}")
        
        print("=" * 60)


def main():
    """Command-line interface for AppImage signature verification."""
    parser = argparse.ArgumentParser(
        description="Verify GPG signatures of AppImage files"
    )
    
    parser.add_argument(
        "appimage",
        help="Path to the AppImage file"
    )
    
    parser.add_argument(
        "-s", "--signature",
        help="Path to the .asc signature file (default: {appimage}.asc)"
    )
    
    parser.add_argument(
        "--gpg-home",
        help="Path to GPG home directory (default: ~/.gnupg)"
    )
    
    args = parser.parse_args()
    
    # Initialize verifier
    verifier = AppImageVerifier(gpg_home=args.gpg_home)
    
    # Verify signature
    result = verifier.verify_signature(args.appimage, args.signature)
    
    # Print results
    verifier.print_verification_result(result, args.appimage)
    
    # Exit with appropriate code
    sys.exit(0 if result['valid'] else 1)


if __name__ == "__main__":
    main()
