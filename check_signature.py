#!/usr/bin/env python3
"""Quick script to check if AppImage has embedded signature"""

import os
from pathlib import Path

appimage_path = Path(r"appimage\7ef8184c-de7a-4a90-804c-7b1580513fc3_968e818b-dacd-49f5-a8fe-b63059e2e353_Nextcloud-4.0.2-x86_64.AppImage")

if not appimage_path.exists():
    print(f"❌ Datei nicht gefunden: {appimage_path}")
    exit(1)

# Read file
with open(appimage_path, 'rb') as f:
    content = f.read()

# Check for embedded signature
has_embedded = b'-----BEGIN PGP SIGNATURE-----' in content
has_asc_file = (Path(str(appimage_path) + ".asc")).exists()

print("=" * 60)
print("SIGNATUR-PRÜFUNG")
print("=" * 60)
print(f"📄 Datei: {appimage_path.name}")
print(f"📊 Größe: {len(content):,} bytes")
print()
print(f"📦 Eingebettete Signatur: {'✓ JA' if has_embedded else '✗ NEIN'}")
print(f"📄 Externe .asc Datei: {'✓ JA' if has_asc_file else '✗ NEIN'}")
print("=" * 60)

if has_embedded:
    # Find position
    pos = content.rfind(b'-----BEGIN PGP SIGNATURE-----')
    print(f"\n✓ Eingebettete Signatur gefunden an Position: {pos:,}")
    print(f"✓ Datengröße vor Signatur: {pos:,} bytes")
    
    # Show first few lines
    sig_data = content[pos:pos+500].decode('utf-8', errors='ignore')
    lines = sig_data.split('\n')[:5]
    print("\nSignatur-Vorschau:")
    for line in lines:
        print(f"  {line}")
