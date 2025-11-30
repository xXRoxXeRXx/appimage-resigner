#!/usr/bin/env python3
"""
Script to embed external .asc signature into AppImage file
"""

import os
import sys
from pathlib import Path

def embed_signature(appimage_path):
    """Embed external .asc signature into AppImage file."""
    appimage_path = Path(appimage_path)
    asc_path = Path(str(appimage_path) + ".asc")
    
    if not appimage_path.exists():
        print(f"❌ AppImage nicht gefunden: {appimage_path}")
        return False
    
    if not asc_path.exists():
        print(f"❌ Signatur-Datei nicht gefunden: {asc_path}")
        return False
    
    print("=" * 60)
    print("SIGNATUR EINBETTEN")
    print("=" * 60)
    print(f"📄 AppImage: {appimage_path.name}")
    print(f"📝 Signatur: {asc_path.name}")
    print()
    
    # Read AppImage
    with open(appimage_path, 'rb') as f:
        appimage_data = f.read()
    
    # Check if already has embedded signature
    if b'-----BEGIN PGP SIGNATURE-----' in appimage_data:
        print("⚠️  AppImage hat bereits eine eingebettete Signatur!")
        user_input = input("Fortfahren und ersetzen? (j/n): ")
        if user_input.lower() != 'j':
            print("Abgebrochen.")
            return False
        
        # Remove existing embedded signature
        sig_start = appimage_data.rfind(b'-----BEGIN PGP SIGNATURE-----')
        # Trim backwards over whitespace
        while sig_start > 0 and appimage_data[sig_start - 1:sig_start] in (b'\n', b'\r', b' ', b'\t'):
            sig_start -= 1
        appimage_data = appimage_data[:sig_start]
        print("✓ Alte eingebettete Signatur entfernt")
    
    # Read signature
    with open(asc_path, 'r', encoding='utf-8') as f:
        signature_data = f.read()
    
    print(f"\n📊 Original AppImage: {len(appimage_data):,} bytes")
    print(f"📊 Signatur: {len(signature_data)} bytes")
    
    # Create backup
    backup_path = Path(str(appimage_path) + ".backup")
    if not backup_path.exists():
        with open(backup_path, 'wb') as f:
            f.write(appimage_data)
        print(f"💾 Backup erstellt: {backup_path.name}")
    
    # Embed signature
    with open(appimage_path, 'wb') as f:
        f.write(appimage_data)
        f.write(b'\n')  # Newline separator
        f.write(signature_data.encode('utf-8'))
    
    # Verify
    with open(appimage_path, 'rb') as f:
        new_content = f.read()
    
    has_embedded = b'-----BEGIN PGP SIGNATURE-----' in new_content
    
    print(f"\n📊 Neue AppImage: {len(new_content):,} bytes")
    print(f"📦 Eingebettete Signatur: {'✓ JA' if has_embedded else '✗ NEIN'}")
    
    if has_embedded:
        print("\n✅ SIGNATUR ERFOLGREICH EINGEBETTET!")
        print("=" * 60)
        return True
    else:
        print("\n❌ FEHLER: Signatur konnte nicht eingebettet werden!")
        print("=" * 60)
        return False

def embed_all_in_directory(directory):
    """Embed signatures for all AppImages in directory."""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ Verzeichnis nicht gefunden: {directory}")
        return
    
    # Find all AppImage files with corresponding .asc files
    appimages = []
    for appimage in directory.glob("*.AppImage"):
        asc_file = Path(str(appimage) + ".asc")
        if asc_file.exists():
            appimages.append(appimage)
    
    if not appimages:
        print(f"⚠️  Keine AppImages mit .asc Dateien gefunden in: {directory}")
        return
    
    print(f"\n🔍 {len(appimages)} AppImage(s) mit .asc Dateien gefunden")
    print("=" * 60)
    
    for i, appimage in enumerate(appimages, 1):
        print(f"\n[{i}/{len(appimages)}] Verarbeite: {appimage.name}")
        print("-" * 60)
        
        success = embed_signature(appimage)
        
        if success:
            print(f"✓ Erfolgreich: {appimage.name}")
        else:
            print(f"✗ Fehlgeschlagen: {appimage.name}")
    
    print("\n" + "=" * 60)
    print("FERTIG!")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python embed_signature.py <appimage_file>")
        print("  python embed_signature.py <directory>  # Verarbeitet alle AppImages im Verzeichnis")
        print("\nBeispiel:")
        print("  python embed_signature.py appimage/Nextcloud.AppImage")
        print("  python embed_signature.py appimage/")
        sys.exit(1)
    
    path = sys.argv[1]
    path_obj = Path(path)
    
    if path_obj.is_dir():
        embed_all_in_directory(path)
    elif path_obj.is_file():
        embed_signature(path)
    else:
        print(f"❌ Pfad nicht gefunden: {path}")
        sys.exit(1)
