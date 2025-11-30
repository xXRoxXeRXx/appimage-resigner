#!/usr/bin/env python3
"""
AppImage Signature Verifier
Verifies GPG signatures of AppImage files.
"""

import sys
import argparse
import gnupg
from pathlib import Path


class AppImageVerifier:
    """Class for verifying AppImage signatures."""
    
    def __init__(self, gpg_home=None):
        """
        Initialize the verifier.
        
        Args:
            gpg_home (str): Path to GPG home directory. Defaults to ~/.gnupg
        """
        self.gpg = gnupg.GPG(gnupghome=gpg_home) if gpg_home else gnupg.GPG()
    
    def verify_signature(self, appimage_path, signature_path=None):
        """
        Verify the GPG signature of an AppImage.
        
        Args:
            appimage_path (str): Path to the AppImage file
            signature_path (str): Path to the .asc signature file.
                                If None, looks for {appimage_path}.asc
        
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
        
        # Determine signature file path
        if signature_path is None:
            signature_path = Path(str(appimage_path) + ".asc")
        else:
            signature_path = Path(signature_path)
        
        if not signature_path.exists():
            return {
                'valid': False,
                'error': f"Signature file not found: {signature_path}"
            }
        
        try:
            # Read the signature file
            with open(signature_path, 'r') as sig_file:
                signature_data = sig_file.read()
            
            # Verify the signature
            with open(appimage_path, 'rb') as data_file:
                verified = self.gpg.verify_data(signature_data, data_file.read())
            
            if verified.valid:
                return {
                    'valid': True,
                    'key_id': verified.key_id,
                    'username': verified.username,
                    'timestamp': verified.sig_timestamp,
                    'fingerprint': verified.fingerprint,
                    'trust_level': verified.trust_text
                }
            else:
                return {
                    'valid': False,
                    'error': f"Invalid signature: {verified.status}",
                    'stderr': verified.stderr
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f"Verification error: {str(e)}"
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
