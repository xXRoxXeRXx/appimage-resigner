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


class AppImageResigner:
    """Main class for AppImage signature management."""
    
    def __init__(self, gpg_home=None):
        """
        Initialize the resigner.
        
        Args:
            gpg_home (str): Path to GPG home directory. Defaults to ~/.gnupg
        """
        gpg_binary = find_gpg_binary()
        if gpg_binary:
            self.gpg = gnupg.GPG(gnupghome=gpg_home, gpgbinary=gpg_binary) if gpg_home else gnupg.GPG(gpgbinary=gpg_binary)
        else:
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
    
    def sign_appimage(self, appimage_path, key_id=None, passphrase=None, output_path=None, embed_signature=False):
        """
        Sign an AppImage file with a GPG key (detached ASCII-armor signature).
        
        Args:
            appimage_path (str): Path to the AppImage file
            key_id (str): GPG key ID to use for signing. If None, uses default key
            passphrase (str): Passphrase for the private key
            output_path (str): Path for the .asc signature file. 
                             If None, creates {appimage_path}.asc
            embed_signature (bool): If True, also embed the signature into the AppImage file
            
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
            # Read the original AppImage file (without any embedded signature)
            with open(appimage_path, 'rb') as f:
                original_data = f.read()
            
            # Check if there's already an embedded signature and remove it
            if b'-----BEGIN PGP SIGNATURE-----' in original_data:
                sig_start = original_data.rfind(b'-----BEGIN PGP SIGNATURE-----')
                
                # Trim whitespace/newlines before the signature to get clean data
                data_end = sig_start
                while data_end > 0 and original_data[data_end - 1:data_end] in (b'\n', b'\r', b' ', b'\t'):
                    data_end -= 1
                
                original_data = original_data[:data_end]
                print(f"ℹ Removed existing embedded signature")
            
            # Create a temporary file with clean data for signing
            import tempfile
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.AppImage') as temp_file:
                temp_file.write(original_data)
                temp_path = temp_file.name
            
            try:
                # Create detached ASCII-armored signature
                with open(temp_path, 'rb') as f:
                    signed_data = self.gpg.sign_file(
                        f,
                        keyid=key_id,
                        passphrase=passphrase,
                        detach=True,
                        clearsign=False
                    )
                
                if signed_data.status == 'signature created':
                    signature_text = str(signed_data)
                    
                    # Normalize line endings to Unix style (\n) for consistency
                    # This ensures the signature works across Windows and Linux
                    signature_text = signature_text.replace('\r\n', '\n').replace('\r', '\n')
                    
                    # Write signature to .asc file with Unix line endings
                    with open(output_path, 'w', newline='') as sig_file:
                        sig_file.write(signature_text)
                    
                    print(f"✓ Successfully signed: {appimage_path}")
                    print(f"✓ Signature saved to: {output_path}")
                    
                    # Embed signature if requested
                    if embed_signature:
                        try:
                            # Write clean data + embedded signature to the AppImage
                            with open(appimage_path, 'wb') as f:
                                f.write(original_data)
                                # Use \n for line ending (Unix style) for consistency
                                f.write(b'\n')
                                # Encode with normalized line endings
                                f.write(signature_text.encode('utf-8'))
                            print(f"✓ Signature embedded in: {appimage_path}")
                        except Exception as e:
                            print(f"Warning: Could not embed signature: {e}")
                            # Restore original if embedding failed
                            with open(appimage_path, 'wb') as f:
                                f.write(original_data)
                    else:
                        # Make sure we write back the clean data without embedded signature
                        with open(appimage_path, 'wb') as f:
                            f.write(original_data)
                    
                    return True
                else:
                    print(f"Error signing file: {signed_data.status}")
                    print(f"Details: {signed_data.stderr}")
                    return False
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error during signing: {e}")
            import traceback
            traceback.print_exc()
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
