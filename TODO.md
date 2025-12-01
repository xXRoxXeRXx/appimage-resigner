# AppImage Re-Signer - Verbesserungen ToDo Liste

## 🔴 Priorität 0 - Kritisch (Sicherheit & Stabilität)

### Security
- [x] **CORS Security Fix** ✅
  - [x] Ersetze `allow_origins=["*"]` durch Environment Variable
  - [x] Erstelle `.env` und `.env.example`
  - [x] Dokumentiere in README

- [x] **File Upload Validation** ✅
  - [x] ELF Header Check implementieren (Magic bytes: 7f 45 4c 46)
  - [x] MIME-Type Validierung hinzufügen
  - [x] AppImage-Format Verifizierung
  - [x] File Size Limit enforcement (nicht nur Config)
  - [x] Tests für verschiedene Dateitypen

- [x] **GPG Key Security** ✅
  - [x] Passphrase nach Verwendung überschreiben
  - [x] Keine Passphrase-Speicherung in Sessions
  - [x] Warnung wenn Passphrase leer
  - [ ] Optional: Hardware Token Support (YubiKey)

### Error Handling & Logging
- [x] **Logging System implementieren** ✅
  - [x] Python `logging` Module einrichten
  - [x] Log-Levels konfigurieren (DEBUG, INFO, WARNING, ERROR)
  - [x] Log-Rotation einrichten
  - [x] Alle `print()` durch `logging` ersetzen
  - [x] Strukturierte Logs (JSON Format optional)
  - [x] Log-File: `logs/appimage-resigner.log`

### Session Management
- [x] **Session Cleanup implementieren** ✅
  - [x] Background-Task für automatisches Cleanup
  - [x] Konfigurierbare Cleanup-Zeit (Standard: 24h)
  - [x] Session-Expiration im Frontend mit Warnung
  - [x] Cron-Job oder APScheduler Integration
  - [x] Cleanup-Status in Health-Check anzeigen

---

## 🟡 Priorität 1 - Wichtig (Features & UX)

### Quick Wins
- [ ] **Health-Check Endpoint**
  - [ ] `/health` Endpoint erstellen
  - [ ] Status, Version, GPG-Verfügbarkeit anzeigen
  - [ ] Timestamp hinzufügen
  - [ ] In Docker HEALTHCHECK verwenden

- [ ] **Version im Footer**
  - [ ] Version in `web/static/index.html` hinzufügen
  - [ ] Version aus Config/Package auslesen
  - [ ] "Made with ❤️" Text

- [ ] **.env Configuration**
  - [ ] `.env.example` erstellen
  - [ ] Environment Variables dokumentieren
  - [ ] pydantic-settings implementieren
  - [ ] Config-Klasse in `web/core/config.py`

- [ ] **requirements.txt aufräumen**
  - [ ] Duplikate entfernen
  - [ ] Kategorien erstellen (Web, GPG, CLI, Testing)
  - [ ] Versionen aktualisieren
  - [ ] Optional dependencies markieren

### Features
- [ ] **Batch-Signierung**
  - [ ] Multi-File Upload im Frontend
  - [ ] Queue-System für mehrere Signiervorgänge
  - [ ] Progress-Tracking pro Datei
  - [ ] Status-Übersicht für alle Dateien
  - [ ] Parallel-Processing (async)

- [ ] **Key Storage & Management**
  - [ ] Keyring-Integration (gpg --list-keys)
  - [ ] Key-Upload mit Wiederverwendung
  - [ ] Dropdown für vorhandene Keys
  - [ ] Key-Metadata anzeigen (Name, Email, Expiry)
  - [ ] Key-Löschung ermöglichen

- [ ] **Download-Verbesserungen**
  - [ ] ZIP-Download beider Dateien (.AppImage + .asc)
  - [ ] Automatischer Dateiname ohne UUID-Prefix
  - [ ] Optional: Direkter Download nach Signierung
  - [ ] Download-Counter/Statistics

- [ ] **Drag & Drop für mehrere Dateien**
  - [ ] Multiple Files Support
  - [ ] Visual Feedback während Drag
  - [ ] File-Queue Anzeige
  - [ ] Einzelne Dateien entfernen können

- [ ] **Progress-Tracking Verbesserung**
  - [ ] XMLHttpRequest statt Fetch für Upload
  - [ ] Prozentuale Progress-Bar
  - [ ] Geschwindigkeits-Anzeige (MB/s)
  - [ ] Verbleibende Zeit schätzen
  - [ ] Status-Nachrichten während Upload

---

## 🟢 Priorität 2 - Nice-to-Have (Komfort)

### Dokumentation
- [ ] **API Dokumentation**
  - [ ] `docs/API.md` erstellen
  - [ ] OpenAPI/Swagger Integration
  - [ ] Endpoint-Beschreibungen
  - [ ] Request/Response Beispiele
  - [ ] Error-Codes dokumentieren

- [ ] **Deployment Guide**
  - [ ] `docs/DEPLOYMENT.md` erstellen
  - [ ] Docker-Setup dokumentieren
  - [ ] Production Best Practices
  - [ ] Reverse-Proxy Config (nginx)
  - [ ] SSL/TLS Setup

- [ ] **Security Guide**
  - [ ] `docs/SECURITY.md` erstellen
  - [ ] Security Best Practices
  - [ ] Vulnerability Reporting
  - [ ] Security Checklist

- [ ] **Examples**
  - [ ] `docs/EXAMPLES.md` erstellen
  - [ ] CLI Beispiele
  - [ ] API Beispiele (curl)
  - [ ] Python Script Beispiele

### Testing
- [ ] **Unit Tests**
  - [ ] `tests/test_resigner.py` - Signing Logic
  - [ ] `tests/test_verify.py` - Verification Logic
  - [ ] `tests/test_key_manager.py` - Key Management
  - [ ] pytest Configuration
  - [ ] Test Coverage >80%

- [ ] **Integration Tests**
  - [ ] `tests/test_web_api.py` - FastAPI Endpoints
  - [ ] `tests/test_gpg.py` - GPG Operations
  - [ ] `tests/test_workflow.py` - End-to-End
  - [ ] pytest-asyncio für async Tests

- [ ] **CI/CD Pipeline**
  - [ ] GitHub Actions Workflow
  - [ ] Automatische Tests bei Push
  - [ ] Code Coverage Report
  - [ ] Linting (black, flake8, mypy)

### Docker Improvements
- [ ] **Multi-stage Build**
  - [ ] Builder Stage für Dependencies
  - [ ] Runtime Stage minimal
  - [ ] Image-Größe optimieren

- [ ] **Security**
  - [ ] Non-root User erstellen
  - [ ] USER Direktive verwenden
  - [ ] HEALTHCHECK hinzufügen
  - [ ] Minimal Base Image (alpine/slim)

- [ ] **Configuration**
  - [ ] Environment Variables
  - [ ] Volume Mounts für Keys
  - [ ] docker-compose.yml erweitern
  - [ ] Production-ready Config

### CLI Enhancement
- [ ] **CLI Tool erstellen**
  - [ ] `cli.py` mit Typer/Click
  - [ ] `sign` Command
  - [ ] `verify` Command
  - [ ] `embed` Command
  - [ ] `list-keys` Command
  - [ ] Help-Text & Dokumentation
  - [ ] Shell-Completion

### UI/UX Improvements
- [ ] **Keyboard Shortcuts**
  - [ ] Strg+V für Paste
  - [ ] Strg+Z für Undo
  - [ ] ESC für Cancel
  - [ ] Enter für Submit

- [ ] **Toast Notifications**
  - [ ] Ersetze `alert()` durch Toast
  - [ ] Success/Error/Info Notifications
  - [ ] Auto-dismiss nach 5 Sekunden
  - [ ] Stack für mehrere Notifications

- [ ] **Mobile-Responsive Design**
  - [ ] Media Queries optimieren
  - [ ] Touch-Gesten Support
  - [ ] Mobile Navigation
  - [ ] Viewport Meta-Tag

- [ ] **Internationalisierung**
  - [ ] i18n Framework (i18next)
  - [ ] Deutsch (DE)
  - [ ] Englisch (EN)
  - [ ] Language Switcher
  - [ ] Locale Storage

- [ ] **Recent Files Liste**
  - [ ] LocalStorage für History
  - [ ] Letzte 10 Dateien anzeigen
  - [ ] Quick-Access zum erneuten Signieren

- [ ] **Undo/Redo**
  - [ ] Action History
  - [ ] Undo/Redo Buttons
  - [ ] State Management

### Performance Optimizations
- [ ] **Streaming Upload**
  - [ ] Chunked Transfer Encoding
  - [ ] Resume-Support
  - [ ] Parallel Chunks
  - [ ] Memory-effizient für große Dateien

- [ ] **WebSocket für Progress**
  - [ ] WebSocket Endpoint `/ws/progress`
  - [ ] Real-time Updates
  - [ ] Reconnect Logic
  - [ ] Fallback zu Polling

- [ ] **Redis Session Storage**
  - [ ] Redis Integration
  - [ ] Session in Redis statt Filesystem
  - [ ] TTL für automatisches Cleanup
  - [ ] Shared Sessions für Load Balancing

- [ ] **Async File Operations**
  - [ ] aiofiles überall verwenden
  - [ ] Async Read/Write
  - [ ] Non-blocking I/O

### Monitoring & Analytics
- [ ] **Prometheus Metrics**
  - [ ] `/metrics` Endpoint
  - [ ] Counter für Signatures
  - [ ] Histogram für Durations
  - [ ] Gauge für active Sessions

- [ ] **Grafana Dashboard**
  - [ ] Dashboard Template
  - [ ] Visualisierung der Metrics
  - [ ] Alerts konfigurieren

- [ ] **Error Tracking**
  - [ ] Sentry Integration (optional)
  - [ ] Error Reports
  - [ ] Stack Traces

### Additional Features
- [ ] **Signature Comparison**
  - [ ] Compare-Endpoint
  - [ ] Diff-Visualisierung
  - [ ] Same Key Check
  - [ ] Timestamp Comparison

- [ ] **Signature History**
  - [ ] Datenbank für History (SQLite)
  - [ ] Alle Signaturen tracken
  - [ ] Wer hat wann was signiert
  - [ ] Export-Funktion

---

## 📊 Code Quality

### Type Hints & Validation
- [ ] **Pydantic Models**
  - [ ] `web/api/models.py` erstellen
  - [ ] SignRequest Model
  - [ ] UploadResponse Model
  - [ ] VerificationResponse Model
  - [ ] Validators für alle Felder

- [ ] **Type Hints überall**
  - [ ] Alle Funktionen annotieren
  - [ ] Return-Types spezifizieren
  - [ ] Optional/Union korrekt verwenden
  - [ ] mypy Checks erfolgreich

### Configuration Management
- [ ] **Settings Klasse**
  - [ ] `web/core/config.py` erstellen
  - [ ] BaseSettings von pydantic
  - [ ] Environment Variables
  - [ ] Validation
  - [ ] .env Support

### Code Struktur
- [ ] **Refactoring**
  - [ ] `web/api/` Package erstellen
  - [ ] `web/core/` Package erstellen
  - [ ] `web/services/` Package erstellen
  - [ ] Routes in `api/routes.py`
  - [ ] Dependencies in `api/deps.py`
  - [ ] Security in `core/security.py`
  - [ ] Exceptions in `core/exceptions.py`

- [ ] **Business Logic trennen**
  - [ ] `services/signing.py`
  - [ ] `services/verification.py`
  - [ ] `services/cleanup.py`
  - [ ] Logic aus Routes entfernen

---

## 🔐 Security Checklist

- [ ] **Rate Limiting**
  - [ ] slowapi installieren
  - [ ] Rate Limits für Endpoints
  - [ ] IP-basiertes Limiting
  - [ ] Konfigurierbare Limits

- [ ] **File Size Enforcement**
  - [ ] Limits vor Upload prüfen
  - [ ] Streaming mit Size-Check
  - [ ] Error wenn zu groß

- [ ] **Virus Scanning**
  - [ ] ClamAV Integration (optional)
  - [ ] Scan nach Upload
  - [ ] Quarantine bei Fund

- [ ] **Input Sanitization**
  - [ ] Path Traversal Prevention
  - [ ] SQL Injection Prevention
  - [ ] XSS Prevention
  - [ ] Command Injection Prevention

- [ ] **HTTPS-Only**
  - [ ] Redirect HTTP → HTTPS
  - [ ] HSTS Header
  - [ ] Secure Cookies

- [ ] **Secret Key Management**
  - [ ] Keine Secrets im Code
  - [ ] Environment Variables
  - [ ] Key Rotation
  - [ ] Secrets Manager (optional)

- [ ] **CSRF Protection**
  - [ ] CSRF Tokens
  - [ ] Same-Site Cookies
  - [ ] Origin Validation

- [ ] **Content Security Policy**
  - [ ] CSP Headers setzen
  - [ ] XSS Prevention
  - [ ] Clickjacking Prevention

- [ ] **Audit Logging**
  - [ ] Wer hat was signiert
  - [ ] IP-Adressen loggen
  - [ ] Timestamps
  - [ ] Compliance-ready

---

## 📋 README Updates

- [ ] **Web Interface Sektion**
  - [ ] Startup-Anleitung
  - [ ] Features auflisten
  - [ ] Screenshots hinzufügen
  - [ ] Browser-Kompatibilität

- [ ] **Installation erweitern**
  - [ ] Docker Installation
  - [ ] Production Setup
  - [ ] Development Setup
  - [ ] Troubleshooting

- [ ] **Contributing Guide**
  - [ ] CONTRIBUTING.md erstellen
  - [ ] Code Style Guidelines
  - [ ] PR Template
  - [ ] Issue Templates

- [ ] **Changelog**
  - [ ] CHANGELOG.md erstellen
  - [ ] Versions-History
  - [ ] Breaking Changes markieren

---

## 🎯 Priorisierung

### Sprint 1 (Quick Wins) - 1-2 Tage
- [x] Live-Preview (bereits implementiert)
- [x] Button Styling (bereits implementiert)
- [x] Signature Bug Fix (bereits implementiert)
- [ ] Health-Check Endpoint
- [ ] .env Configuration
- [ ] Version im Footer
- [ ] requirements.txt aufräumen

### Sprint 2 (Security) - 3-5 Tage
- [ ] Logging System
- [ ] Session Cleanup
- [ ] File Upload Validation
- [ ] CORS Security
- [ ] Error Handling

### Sprint 3 (Testing) - 3-5 Tage
- [ ] Unit Tests schreiben
- [ ] Integration Tests
- [ ] CI/CD Pipeline
- [ ] Coverage >80%

### Sprint 4 (Features) - 5-7 Tage
- [ ] Batch-Signierung
- [ ] Key Management
- [ ] Download-Verbesserungen
- [ ] Progress-Tracking

### Sprint 5 (Quality) - 3-5 Tage
- [ ] Type Hints überall
- [ ] Code Refactoring
- [ ] Documentation
- [ ] Docker Improvements

---

## 📝 Notizen

- **Bereits implementiert:**
  - ✅ IONOS Design System
  - ✅ Embedded Signatures
  - ✅ Live-Preview Metadata
  - ✅ Dark Mode
  - ✅ Copy-to-Clipboard
  - ✅ Signature Verification Fix

- **In Arbeit:**
  - 🔄 Session Cleanup (geplant)
  - 🔄 Health-Check (geplant)

- **Blockiert:**
  - ❌ Keine Blocker

---

**Letzte Aktualisierung:** 01.12.2025
**Version:** 2.0.0
**Status:** In aktiver Entwicklung 🚀
