# AppImage Re-Signer - Web Interface

Web-basierte Benutzeroberfläche für das AppImage Re-Signing Tool.

## 🌐 Features

- **📤 Drag & Drop Upload**: AppImages und GPG Keys einfach hochladen
- **🔄 Automatisches Re-Signing**: Alte Signatur entfernen und neue erstellen
- **✅ Live-Verifikation**: Signatur-Details direkt anzeigen
- **💾 Download**: Signierte AppImage und .asc Datei herunterladen
- **🔒 Sicherheit**: Temporäre Dateien werden automatisch nach 24h gelöscht

## 🚀 Schnellstart

### Option 1: Mit Docker (empfohlen)

```bash
# Docker Container bauen und starten
docker-compose up -d

# Web-Interface öffnen
# http://localhost:8000
```

### Option 2: Lokale Installation

```bash
# Dependencies installieren
pip install -r requirements.txt

# Server starten
python -m uvicorn web.app:app --reload --host 0.0.0.0 --port 8000

# Web-Interface öffnen
# http://localhost:8000
```

## 📖 Verwendung

1. **AppImage hochladen**
   - Drag & Drop oder Dateiauswahl
   
2. **GPG Key bereitstellen**
   - **Option A**: Key-Datei hochladen
   - **Option B**: Key-ID eingeben (Key muss im System vorhanden sein)
   - Optional: Passphrase eingeben

3. **Signieren**
   - Button klicken und warten
   - Signatur wird erstellt und verifiziert

4. **Download**
   - Signierte AppImage herunterladen
   - .asc Signatur-Datei herunterladen

## 🔧 API Endpoints

### Session Management
- `POST /api/session/create` - Neue Session erstellen
- `GET /api/session/{session_id}/status` - Session-Status abrufen
- `DELETE /api/session/{session_id}` - Session löschen

### File Operations
- `POST /api/upload/appimage` - AppImage hochladen
- `POST /api/upload/key` - GPG Key hochladen
- `POST /api/sign` - AppImage signieren
- `GET /api/verify/{session_id}` - Signatur verifizieren
- `GET /api/download/appimage/{session_id}` - Signierte AppImage herunterladen
- `GET /api/download/signature/{session_id}` - Signatur-Datei herunterladen

### API Dokumentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐳 Docker Deployment

### Development
```bash
docker-compose up
```

### Production
```bash
# Mit Umgebungsvariablen
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables
```env
# Optional
MAX_FILE_SIZE=524288000  # 500 MB in bytes
CLEANUP_AFTER_HOURS=24
```

## 🔒 Sicherheitshinweise

### Für Produktion:

1. **CORS konfigurieren**
   ```python
   # In web/app.py
   allow_origins=["https://your-domain.com"]
   ```

2. **HTTPS verwenden**
   - Reverse Proxy (nginx/traefik)
   - SSL-Zertifikate (Let's Encrypt)

3. **Authentifizierung hinzufügen**
   - OAuth2, JWT tokens
   - Rate limiting

4. **File Upload Limits**
   - Nginx: `client_max_body_size`
   - FastAPI: MAX_FILE_SIZE anpassen

5. **Temporäre Dateien**
   - Werden automatisch nach 24h gelöscht
   - Regelmäßige Cleanup-Jobs einrichten

## 📊 Systemanforderungen

- Python 3.11+
- GPG/GnuPG installiert
- Mindestens 1 GB RAM
- Ausreichend Speicherplatz für AppImages

## 🛠️ Entwicklung

### Lokaler Dev-Server
```bash
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend bearbeiten
- HTML: `web/static/index.html`
- CSS: `web/static/style.css`
- JavaScript: `web/static/app.js`

### Backend bearbeiten
- FastAPI App: `web/app.py`
- Signing Logic: `src/resigner.py`

## 🐛 Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "GPG not found"
```bash
# Ubuntu/Debian
sudo apt-get install gnupg

# macOS
brew install gnupg

# Windows
# Gpg4win installieren
```

### "Port already in use"
```bash
# Anderen Port verwenden
uvicorn web.app:app --port 8001
```

### Upload fehlschlägt
- Prüfe Datei-Größe (Max 500 MB)
- Prüfe Dateityp (.AppImage)
- Prüfe Schreibrechte für `uploads/` Verzeichnis

## 📝 Lizenz

[Ihre Lizenz]

---

**Entwicklungszeit:** ~6 Stunden für CLI + Web Interface statt 2 Tage! 🚀
