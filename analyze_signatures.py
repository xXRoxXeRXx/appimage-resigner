#!/usr/bin/env python3
"""
Analyze the exact bytes before embedded signatures
"""

from pathlib import Path

def analyze_signature_position(filepath):
    """Analyze bytes around signature"""
    with open(filepath, 'rb') as f:
        content = f.read()
        
    if b'-----BEGIN PGP SIGNATURE-----' not in content:
        print(f"{filepath.name}: No embedded signature")
        return
    
    sig_start = content.rfind(b'-----BEGIN PGP SIGNATURE-----')
    
    # Show 50 bytes before signature
    start = max(0, sig_start - 50)
    before_sig = content[start:sig_start]
    
    print(f"\n{'='*60}")
    print(f"File: {filepath.name}")
    print(f"Signature position: {sig_start}")
    print(f"\nLast 50 bytes before signature (hex):")
    print(before_sig.hex())
    print(f"\nLast 20 bytes before signature (repr):")
    print(repr(before_sig[-20:]))
    print(f"\nLast 10 bytes analysis:")
    for i in range(min(10, len(before_sig))):
        byte_pos = len(before_sig) - 10 + i
        if byte_pos >= 0:
            byte_val = before_sig[byte_pos]
            if byte_val == ord(b'\n'):
                char_repr = '\\n (LF)'
            elif byte_val == ord(b'\r'):
                char_repr = '\\r (CR)'
            elif byte_val == 0:
                char_repr = '\\x00 (NULL)'
            elif 32 <= byte_val < 127:
                char_repr = f"'{chr(byte_val)}'"
            else:
                char_repr = f'\\x{byte_val:02x}'
            print(f"  [-{10-i}] = {byte_val:3d} (0x{byte_val:02x}) = {char_repr}")


# Test files
test_dir = Path("signed")
if test_dir.exists():
    for file in list(test_dir.glob("*.AppImage"))[:5]:
        try:
            analyze_signature_position(file)
        except Exception as e:
            print(f"\nError analyzing {file.name}: {e}")

test_dir = Path("appimage")
if test_dir.exists():
    for file in list(test_dir.glob("*.AppImage"))[:3]:
        try:
            analyze_signature_position(file)
        except Exception as e:
            print(f"\nError analyzing {file.name}: {e}")
