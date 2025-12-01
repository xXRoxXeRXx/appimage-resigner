#!/usr/bin/env python3
"""
AppImage Signature Verifier
Verifies GPG signatures of AppImage files.
"""

import sys
import os
import argparse
import gnupg  # type: ignore[import]
import shutil
import base64
import struct
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


def find_gpg_binary() -> Optional[str]:
    """Find GPG binary on the system.
    
    Returns:
        Path to GPG binary if found, None otherwise
    """
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
    
    gpg: gnupg.GPG
    
    def __init__(self, gpg_home: Optional[str] = None) -> None:
        """
        Initialize the verifier.
        
        Args:
            gpg_home: Path to GPG home directory. Defaults to ~/.gnupg
        """
        gpg_binary = find_gpg_binary()
        if gpg_binary:
            self.gpg = gnupg.GPG(gnupghome=gpg_home, gpgbinary=gpg_binary) if gpg_home else gnupg.GPG(gpgbinary=gpg_binary)
        else:
            self.gpg = gnupg.GPG(gnupghome=gpg_home) if gpg_home else gnupg.GPG()
    
    def get_signature_info(self, appimage_path: str) -> Dict[str, Any]:
        """
        Get information about a signature without verifying it.
        Just checks if a signature exists and extracts basic info + metadata.
        
        Args:
            appimage_path: Path to the AppImage file
            
        Returns:
            Signature information (has_signature, type, signature_data, metadata)
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
                    
                    # Parse metadata
                    metadata = parse_signature_metadata(sig_data)
                    
                    # Extract just the first few lines for display
                    sig_lines = sig_data.split('\n')
                    sig_preview = '\n'.join(sig_lines[:10])
                    
                    return {
                        'has_signature': True,
                        'type': 'embedded',
                        'signature_data': sig_preview + '\n...' if len(sig_lines) > 10 else sig_data,
                        'size': len(sig_data),
                        'metadata': metadata
                    }
            
            # Check for external .asc file
            asc_path = Path(str(appimage_path) + ".asc")
            if asc_path.exists():
                with open(asc_path, 'r') as f:
                    sig_data = f.read()
                    
                    # Parse metadata
                    metadata = parse_signature_metadata(sig_data)
                    
                    sig_lines = sig_data.split('\n')
                    sig_preview = '\n'.join(sig_lines[:10])
                    
                    return {
                        'has_signature': True,
                        'type': 'external',
                        'signature_data': sig_preview + '\n...' if len(sig_lines) > 10 else sig_data,
                        'size': len(sig_data),
                        'metadata': metadata
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
    
    def extract_embedded_signature(self, appimage_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract embedded signature from AppImage file.
        AppImages can have their signature embedded at the end of the file.
        
        Args:
            appimage_path: Path to the AppImage file
            
        Returns:
            Signature information or None if no signature found
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
                    # Support both Windows (\r\n) and Unix (\n) line endings
                    while data_end > 0 and content[data_end - 1:data_end] in (b'\n', b'\r', b' ', b'\t'):
                        data_end -= 1
                    
                    # Extract signature block
                    sig_data_bytes = content[sig_start:]
                    
                    # IMPORTANT: Normalize line endings in signature to \n (Unix style)
                    # This ensures consistency regardless of how the signature was created
                    sig_data = sig_data_bytes.decode('utf-8', errors='ignore')
                    sig_data = sig_data.replace('\r\n', '\n').replace('\r', '\n')
                    
                    # Get the data before the signature (this is what was signed)
                    data_before_sig = content[:data_end]
                    
                    print(f"🔍 Data size before signature: {len(data_before_sig)} bytes (trimmed from {sig_start})")
                    print(f"🔍 Signature size: {len(sig_data)} bytes (normalized line endings)")
                    print(f"🔍 Last 20 bytes of data: {data_before_sig[-20:].hex()}")
                    print(f"🔍 First 50 chars of signature: {sig_data[:50]}")
                    
                    # Save to temporary files for verification
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.data') as data_file:
                        data_file.write(data_before_sig)
                        data_path = data_file.name
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.asc', newline='') as sig_file:
                        # Write with Unix line endings for GPG compatibility
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
    
    def verify_signature(
        self,
        appimage_path: str,
        signature_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify the GPG signature of an AppImage.
        
        Args:
            appimage_path: Path to the AppImage file
            signature_path: Path to the .asc signature file.
                           If None, tries embedded signature first, then looks for .asc
        
        Returns:
            Verification result with keys:
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
    
    def print_verification_result(self, result: Dict[str, Any], appimage_path: str) -> None:
        """
        Pretty print verification results.
        
        Args:
            result: Verification result from verify_signature()
            appimage_path: Path to the AppImage file
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


def main() -> None:
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


def get_algorithm_name(algo_id: int) -> str:
    """
    Get human-readable name for public key algorithm.
    
    Args:
        algo_id: Algorithm ID from PGP packet
        
    Returns:
        str: Algorithm name
    """
    algorithms = {
        1: 'RSA (Encrypt or Sign)',
        2: 'RSA (Encrypt Only)',
        3: 'RSA (Sign Only)',
        16: 'Elgamal (Encrypt Only)',
        17: 'DSA (Digital Signature Algorithm)',
        18: 'ECDH (Elliptic Curve)',
        19: 'ECDSA (Elliptic Curve Digital Signature Algorithm)',
        22: 'EdDSA (Ed25519/Ed448)',
        23: 'AEDH',
        24: 'AEDSA',
    }
    return algorithms.get(algo_id, f'Unknown Algorithm ({algo_id})')


def get_hash_algorithm_name(hash_id: int) -> str:
    """
    Get human-readable name for hash algorithm.
    
    Args:
        hash_id: Hash algorithm ID from PGP packet
        
    Returns:
        str: Hash algorithm name
    """
    hash_algorithms = {
        1: 'MD5',
        2: 'SHA-1',
        3: 'RIPEMD-160',
        8: 'SHA-256',
        9: 'SHA-384',
        10: 'SHA-512',
        11: 'SHA-224',
    }
    return hash_algorithms.get(hash_id, f'Unknown Hash ({hash_id})')


def parse_signature_metadata(signature_data: str) -> dict:
    """
    Parse PGP signature to extract metadata without GPG verification.
    Parses the ASCII-armored signature format.
    
    Args:
        signature_data: ASCII-armored PGP signature
        
    Returns:
        dict: Metadata including algorithm, hash, timestamp, key ID, etc.
    """
    metadata = {
        'raw_available': False,
        'algorithm': None,
        'hash_algorithm': None,
        'timestamp': None,
        'timestamp_readable': None,
        'key_id': None,
        'signature_type': None,
        'version': None,
    }
    
    try:
        # Extract base64 data between BEGIN and END markers
        lines = signature_data.split('\n')
        base64_lines = []
        in_signature = False
        
        for line in lines:
            line = line.strip()
            if 'BEGIN PGP SIGNATURE' in line:
                in_signature = True
                continue
            if 'END PGP SIGNATURE' in line:
                break
            if in_signature and line and not line.startswith('='):
                base64_lines.append(line)
        
        if not base64_lines:
            return metadata
        
        # Decode base64
        base64_data = ''.join(base64_lines)
        try:
            decoded = base64.b64decode(base64_data)
        except Exception as e:
            metadata['parse_error'] = f'Base64 decode error: {str(e)}'
            return metadata
        
        if len(decoded) < 10:
            metadata['parse_error'] = 'Signature data too short'
            return metadata
        
        metadata['raw_available'] = True
        
        # Parse OpenPGP packet structure
        # Reference: RFC 4880 (OpenPGP Message Format)
        
        idx = 0
        packet_tag = decoded[idx]
        idx += 1
        
        # Check if it's a new format packet (bit 6 set)
        if packet_tag & 0x40:
            # New format packet
            packet_type = packet_tag & 0x3f
            
            # Read packet length (simplified for common case)
            if idx < len(decoded):
                length_byte = decoded[idx]
                idx += 1
                
                if length_byte < 192:
                    packet_length = length_byte
                elif length_byte < 224:
                    if idx < len(decoded):
                        packet_length = ((length_byte - 192) << 8) + decoded[idx] + 192
                        idx += 1
        else:
            # Old format packet
            packet_type = (packet_tag >> 2) & 0x0f
            length_type = packet_tag & 0x03
            
            # Read length based on length_type
            if length_type == 0:
                packet_length = decoded[idx] if idx < len(decoded) else 0
                idx += 1
            elif length_type == 1:
                packet_length = struct.unpack('>H', decoded[idx:idx+2])[0] if idx+1 < len(decoded) else 0
                idx += 2
            elif length_type == 2:
                packet_length = struct.unpack('>I', decoded[idx:idx+4])[0] if idx+3 < len(decoded) else 0
                idx += 4
        
        # Packet type 2 = Signature Packet
        if packet_type == 2:
            if idx >= len(decoded):
                return metadata
            
            # Version
            version = decoded[idx]
            metadata['version'] = version
            idx += 1
            
            if version == 4 or version == 5:
                # Version 4/5 signature
                if idx >= len(decoded):
                    return metadata
                
                sig_type = decoded[idx]
                metadata['signature_type'] = sig_type
                idx += 1
                
                if idx >= len(decoded):
                    return metadata
                    
                pub_key_algo = decoded[idx]
                metadata['algorithm'] = get_algorithm_name(pub_key_algo)
                metadata['algorithm_id'] = pub_key_algo
                idx += 1
                
                if idx >= len(decoded):
                    return metadata
                    
                hash_algo = decoded[idx]
                metadata['hash_algorithm'] = get_hash_algorithm_name(hash_algo)
                metadata['hash_algorithm_id'] = hash_algo
                idx += 1
                
                # Hashed subpacket data length
                if idx + 1 >= len(decoded):
                    return metadata
                    
                hashed_length = struct.unpack('>H', decoded[idx:idx+2])[0]
                idx += 2
                
                # Parse hashed subpackets for timestamp and other data
                subpacket_end = idx + hashed_length
                while idx < subpacket_end and idx < len(decoded):
                    # Subpacket length
                    if decoded[idx] < 192:
                        sub_length = decoded[idx]
                        idx += 1
                    elif decoded[idx] < 255:
                        if idx + 1 >= len(decoded):
                            break
                        sub_length = ((decoded[idx] - 192) << 8) + decoded[idx+1] + 192
                        idx += 2
                    else:
                        if idx + 4 >= len(decoded):
                            break
                        sub_length = struct.unpack('>I', decoded[idx+1:idx+5])[0]
                        idx += 5
                    
                    if idx >= len(decoded) or sub_length < 1:
                        break
                    
                    sub_type = decoded[idx]
                    idx += 1
                    sub_length -= 1
                    
                    # Subpacket type 2 = Signature Creation Time
                    if sub_type == 2 and sub_length == 4:
                        if idx + 4 <= len(decoded):
                            timestamp = struct.unpack('>I', decoded[idx:idx+4])[0]
                            metadata['timestamp'] = timestamp
                            metadata['timestamp_readable'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Subpacket type 16 = Issuer Key ID
                    elif sub_type == 16 and sub_length == 8:
                        if idx + 8 <= len(decoded):
                            key_id_bytes = decoded[idx:idx+8]
                            metadata['key_id'] = ''.join(f'{b:02X}' for b in key_id_bytes)
                    
                    idx += sub_length
            
            elif version == 3:
                # Version 3 signature (older format)
                # Skip length of hashed material (1 byte)
                idx += 1
                
                if idx >= len(decoded):
                    return metadata
                    
                sig_type = decoded[idx]
                metadata['signature_type'] = sig_type
                idx += 1
                
                # Timestamp (4 bytes)
                if idx + 4 <= len(decoded):
                    timestamp = struct.unpack('>I', decoded[idx:idx+4])[0]
                    metadata['timestamp'] = timestamp
                    metadata['timestamp_readable'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    idx += 4
                
                # Key ID (8 bytes)
                if idx + 8 <= len(decoded):
                    key_id_bytes = decoded[idx:idx+8]
                    metadata['key_id'] = ''.join(f'{b:02X}' for b in key_id_bytes)
                    idx += 8
                
                # Public key algorithm
                if idx < len(decoded):
                    pub_key_algo = decoded[idx]
                    metadata['algorithm'] = get_algorithm_name(pub_key_algo)
                    metadata['algorithm_id'] = pub_key_algo
                    idx += 1
                
                # Hash algorithm
                if idx < len(decoded):
                    hash_algo = decoded[idx]
                    metadata['hash_algorithm'] = get_hash_algorithm_name(hash_algo)
                    metadata['hash_algorithm_id'] = hash_algo
    
    except Exception as e:
        metadata['parse_error'] = f'Parse error: {str(e)}'
    
    return metadata


if __name__ == "__main__":
    main()
