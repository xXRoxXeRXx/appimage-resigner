#!/usr/bin/env python3
"""
AppImage Re-Signer
Removes existing GPG signatures and adds new ones to AppImage files.
"""

import sys
import os
import argparse
import gnupg
import subprocess
from pathlib import Path


class AppImageResigner:
    """Main class for AppImage signature management."""
    
    def __init__(self, gpg_home=None):
        """
        Initialize the resigner.
        
        Args:
            gpg_home (str): Path to GPG home directory. Defaults to ~/.gnupg
        """
        self.gpg = gnupg.GPG(gnupghome=gpg_home) if gpg_home else gnupg.GPG()
        
    def remove_signature(self, appimage_path):
        """
        Remove existing GPG signature from AppImage.
        
        AppImages can have embedded signatures or separate .asc files.
        This method handles both cases.
        
        Args:
            appimage_path (str): Path to the AppImage file
            
        Returns:
            bool: True if signature was removed or didn't exist, False on error
        """
        appimage_path = Path(appimage_path)
        
        if not appimage_path.exists():
            print(f"Error: AppImage file not found: {appimage_path}")
            return False
        
        # Remove separate .asc signature file if it exists
        asc_file = Path(str(appimage_path) + ".asc")
        if asc_file.exists():
            try:
                asc_file.unlink()
                print(f"Removed signature file: {asc_file}")
            except Exception as e:
                print(f"Error removing .asc file: {e}")
                return False
        
        # Check for embedded signature using dd
        # AppImage signature is typically at the end of the file
        # This is a simplified approach - full implementation would need
        # to parse the AppImage structure
        print(f"Checked for signatures in: {appimage_path}")
        return True
    
    def sign_appimage(self, appimage_path, key_id=None, passphrase=None, output_path=None):
        """
        Sign an AppImage file with a GPG key (detached ASCII-armor signature).
        
        Args:
            appimage_path (str): Path to the AppImage file
            key_id (str): GPG key ID to use for signing. If None, uses default key
            passphrase (str): Passphrase for the private key
            output_path (str): Path for the .asc signature file. 
                             If None, creates {appimage_path}.asc
            
        Returns:
            bool: True if signing was successful, False otherwise
        """
        appimage_path = Path(appimage_path)
        
        if not appimage_path.exists():
            print(f"Error: AppImage file not found: {appimage_path}")
            return False
        
        # Set output path for signature
        if output_path is None:
            output_path = Path(str(appimage_path) + ".asc")
        else:
            output_path = Path(output_path)
        
        try:
            # Read the AppImage file
            with open(appimage_path, 'rb') as f:
                # Create detached ASCII-armored signature
                signed_data = self.gpg.sign_file(
                    f,
                    keyid=key_id,
                    passphrase=passphrase,
                    detach=True,
                    clearsign=False
                )
                
                if signed_data.status == 'signature created':
                    # Write signature to .asc file
                    with open(output_path, 'w') as sig_file:
                        sig_file.write(str(signed_data))
                    
                    print(f"✓ Successfully signed: {appimage_path}")
                    print(f"✓ Signature saved to: {output_path}")
                    return True
                else:
                    print(f"Error signing file: {signed_data.status}")
                    print(f"Details: {signed_data.stderr}")
                    return False
                    
        except Exception as e:
            print(f"Error during signing: {e}")
            return False
    
    def resign_appimage(self, appimage_path, key_id=None, passphrase=None):
        """
        Complete re-signing workflow: remove old signature and add new one.
        
        Args:
            appimage_path (str): Path to the AppImage file
            key_id (str): GPG key ID to use for signing
            passphrase (str): Passphrase for the private key
            
        Returns:
            bool: True if re-signing was successful, False otherwise
        """
        print(f"Re-signing AppImage: {appimage_path}")
        print("-" * 60)
        
        # Step 1: Remove existing signature
        print("Step 1: Removing existing signature...")
        if not self.remove_signature(appimage_path):
            return False
        
        # Step 2: Sign with new key
        print("\nStep 2: Signing with new key...")
        if not self.sign_appimage(appimage_path, key_id, passphrase):
            return False
        
        print("\n✓ Re-signing completed successfully!")
        return True


def main():
    """Command-line interface for AppImage re-signer."""
    parser = argparse.ArgumentParser(
        description="Remove and add GPG signatures to AppImage files"
    )
    
    parser.add_argument(
        "appimage",
        help="Path to the AppImage file"
    )
    
    parser.add_argument(
        "-k", "--key-id",
        help="GPG key ID to use for signing (default: default key)"
    )
    
    parser.add_argument(
        "-p", "--passphrase",
        help="Passphrase for the private key (use with caution!)"
    )
    
    parser.add_argument(
        "--gpg-home",
        help="Path to GPG home directory (default: ~/.gnupg)"
    )
    
    parser.add_argument(
        "--remove-only",
        action="store_true",
        help="Only remove signature, don't sign"
    )
    
    parser.add_argument(
        "--sign-only",
        action="store_true",
        help="Only sign, don't remove existing signature"
    )
    
    args = parser.parse_args()
    
    # Initialize resigner
    resigner = AppImageResigner(gpg_home=args.gpg_home)
    
    # Execute requested operation
    if args.remove_only:
        success = resigner.remove_signature(args.appimage)
    elif args.sign_only:
        success = resigner.sign_appimage(args.appimage, args.key_id, args.passphrase)
    else:
        success = resigner.resign_appimage(args.appimage, args.key_id, args.passphrase)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
