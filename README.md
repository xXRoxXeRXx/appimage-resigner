# AppImage Re-Signer

Ein Python-Tool zum Entfernen und Hinzufügen von GPG-Signaturen bei Linux AppImage-Dateien.

## 🎯 Projektübersicht

Dieses Tool löst das Problem, wenn AppImages aus automatisierten Build-Prozessen stammen und mit einer eigenen GPG-Signatur versehen werden müssen. Es ermöglicht das Re-Signieren von AppImages in wenigen Schritten.

## ✨ Features

- ✅ Entfernen bestehender GPG-Signaturen von AppImages
- ✅ Signieren von AppImages mit eigenem GPG-Key
- ✅ Detached ASCII-Armor Signaturen (.asc Dateien)
- ✅ Verifizierung von AppImage-Signaturen
- ✅ GPG Key Management (Generierung, Import, Export)
- ✅ CLI und programmatische Nutzung
- ✅ Kompatibel mit Nextcloud AppImage-Signatur-Standard

## 📋 Voraussetzungen

- Python 3.7 oder höher
- GPG (GnuPG) installiert auf dem System
  - **Linux:** `sudo apt install gnupg` (Debian/Ubuntu) oder `yum install gnupg` (RHEL/CentOS)
  - **macOS:** `brew install gnupg`
  - **Windows:** [Gpg4win](https://gpg4win.org/)

## 🚀 Installation

### 1. Repository klonen
```bash
git clone <repository-url>
cd appimage-resigner
```

### 2. Virtual Environment erstellen (empfohlen)
```bash
python -m venv venv
source venv/bin/activate  # Auf Windows: venv\Scripts\activate
```

### 3. Dependencies installieren
```bash
pip install -r requirements.txt
```

## 📖 Verwendung

### 1. GPG Key Pair erstellen

Zuerst erstellen Sie ein GPG Key-Pair mit Ihren Metadaten:

```bash
python src/key_manager.py generate \
    --name "Company AppImage Signing" \
    --email "signing@company.example" \
    --comment "AppImage Code Signing Key" \
    --passphrase "IhrSicheresPasswort" \
    --no-expire
```

**Wichtig:** 
- `--no-expire` verhindert Kompatibilitätsprobleme (wie bei Nextcloud)
- Passphrase sicher im Passwortmanager aufbewahren

### 2. GPG Keys auflisten

```bash
# Public Keys anzeigen
python src/key_manager.py list

# Private Keys anzeigen
python src/key_manager.py list --secret
```

### 3. AppImage signieren

#### Komplettes Re-Signing (alte Signatur entfernen + neu signieren)
```bash
python src/resigner.py your-app.AppImage \
    --key-id YOUR_KEY_ID \
    --passphrase "IhrPasswort"
```

#### Nur signieren (ohne Entfernen)
```bash
python src/resigner.py your-app.AppImage \
    --sign-only \
    --key-id YOUR_KEY_ID \
    --passphrase "IhrPasswort"
```

#### Nur alte Signatur entfernen
```bash
python src/resigner.py your-app.AppImage --remove-only
```

### 4. Signatur verifizieren

```bash
python src/verify.py your-app.AppImage
```

Dies prüft die Signatur und zeigt Details wie Key-ID, Fingerprint und Gültigkeit an.

### 5. Keys exportieren

#### Public Key exportieren (für Website)
```bash
python src/key_manager.py export YOUR_KEY_ID public-key.asc
```

#### Private Key exportieren (zur sicheren Aufbewahrung)
```bash
python src/key_manager.py export YOUR_KEY_ID private-key.asc \
    --secret \
    --passphrase "IhrPasswort"
```

**⚠️ WICHTIG:** Private Keys extrem sicher aufbewahren!

### 6. Keys importieren

```bash
python src/key_manager.py import key-file.asc
```

## 🔄 Workflow 

### Einmaliges Setup:

1. **GPG Key-Pair erstellen** 
2. **Public Key exportieren** 
3. **Private Key sicher aufbewahren** im Passwortmanager
4. **Revocation Certificate erstellen** (manuell via GPG):
   ```bash
   gpg --output revoke.asc --gen-revoke YOUR_KEY_ID
   ```

### Für jeden Build:

1. **AppImage vom Brander empfangen**
2. **Re-Signing durchführen:**
   ```bash
   python src/resigner.py app.AppImage --key-id YOUR_KEY_ID --passphrase "..."
   ```
3. **Verifizieren:**
   ```bash
   python src/verify.py app.AppImage
   ```
4. **Bereitstellen:**
   - `app.AppImage` - Die signierte Anwendung
   - `app.AppImage.asc` - Die Signaturdatei
   - `public-key.asc` - Der öffentliche Schlüssel (auf Website)

### Veröffentlichung:

Auf der Download-Seite bereitstellen:
- ✅ `app.AppImage` - Die Anwendung
- ✅ `app.AppImage.asc` - Die Signatur
- ✅ `public-key.asc` - Öffentlicher Key zur Verifikation
- ✅ Anleitung zur Verifikation für Endnutzer

## 🔐 Signatur-Verifikation für Endnutzer

Anleitung für Benutzer auf der Download-Seite:

```bash
# 1. Public Key importieren
gpg --import public-key.asc

# 2. Signatur verifizieren
gpg --verify app.AppImage.asc app.AppImage

# 3. Bei erfolgreicher Verifikation wird angezeigt:
# "Good signature from 'Company AppImage Signing <signing@company.example>'"
```

## 🔧 Programmatische Verwendung

```python
from src.resigner import AppImageResigner
from src.verify import AppImageVerifier
from src.key_manager import GPGKeyManager

# Re-Signing
resigner = AppImageResigner()
resigner.resign_appimage(
    "app.AppImage", 
    key_id="YOUR_KEY_ID",
    passphrase="your-passphrase"
)

# Verifikation
verifier = AppImageVerifier()
result = verifier.verify_signature("app.AppImage")
print(f"Gültig: {result['valid']}")

# Key Management
manager = GPGKeyManager()
manager.generate_key(
    name="Company AppImage Signing",
    email="signing@company.example",
    passphrase="your-passphrase"
)
```

## 🏗️ CI/CD Integration

### GitHub Actions Beispiel:

```yaml
name: Sign AppImage

on: [push]

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Import GPG key
        run: |
          echo "${{ secrets.GPG_PRIVATE_KEY }}" | gpg --import
          
      - name: Sign AppImage
        run: |
          python src/resigner.py build/app.AppImage \
            --key-id ${{ secrets.GPG_KEY_ID }} \
            --passphrase ${{ secrets.GPG_PASSPHRASE }}
          
      - name: Verify signature
        run: |
          python src/verify.py build/app.AppImage
          
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: signed-appimage
          path: |
            build/app.AppImage
            build/app.AppImage.asc
```

## 📁 Projektstruktur

```
appimage-resigner/
├── src/
│   ├── __init__.py
│   ├── resigner.py        # Hauptprogramm für Re-Signing
│   ├── verify.py          # Signatur-Verifikation
│   └── key_manager.py     # GPG Key Management
├── tests/
│   └── __init__.py
├── .github/
│   └── copilot-instructions.md
├── requirements.txt       # Python-Dependencies
├── .gitignore
└── README.md
```

## 🔒 Sicherheitshinweise

1. **Private Keys niemals committen!**
   - Sind bereits in `.gitignore` ausgeschlossen
   - Immer im Passwortmanager aufbewahren

2. **Passphrasen sicher behandeln:**
   - Nicht hardcoden
   - Umgebungsvariablen oder Secret Manager verwenden
   - Für CI/CD: GitHub Secrets, GitLab Variables, etc.

3. **Revocation Certificate erstellen:**
   - Sofort nach Key-Erstellung
   - Sicher aufbewahren für Notfall-Widerruf

4. **Key Rotation:**
   - Keys regelmäßig rotieren (z.B. alle 2 Jahre)
   - Oder ohne Ablaufdatum für maximale Kompatibilität

## 🐛 Troubleshooting

### "Import gnupg could not be resolved"
```bash
pip install python-gnupg
```

### "gpg: signing failed: No secret key"
```bash
# Private Key importieren
python src/key_manager.py import private-key.asc
```

### "Signature verification failed"
- Public Key korrekt importiert? `gpg --list-keys`
- Signatur-Datei (.asc) vorhanden?
- AppImage nach Signierung nicht verändert?

### GPG nicht gefunden (Windows)
- Gpg4win installieren: https://gpg4win.org/
- GPG zum PATH hinzufügen

## 📚 Weitere Ressourcen

- [GnuPG Documentation](https://gnupg.org/documentation/)
- [python-gnupg Documentation](https://gnupg.readthedocs.io/)
- [AppImage Specification](https://docs.appimage.org/)
- [Nextcloud AppImage Signing](https://github.com/nextcloud/desktop/wiki/AppImage-Signing) - Referenz-Beispiel