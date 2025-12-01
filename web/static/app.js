// AppImage Re-Signer - Frontend Logic

// Dark Mode Management
function initDarkMode() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('theme-icon').textContent = '☀️';
    }
}

function toggleDarkMode() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        document.getElementById('theme-icon').textContent = '🌙';
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('theme-icon').textContent = '☀️';
        localStorage.setItem('theme', 'dark');
    }
}

// Load version from server
async function loadVersion() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        if (data.version) {
            const versionBadge = document.getElementById('app-version');
            if (versionBadge) {
                versionBadge.textContent = `v${data.version}`;
            }
        }
    } catch (error) {
        console.error('Could not load version:', error);
    }
}

// Initialize dark mode on load
document.addEventListener('DOMContentLoaded', async () => {
    initDarkMode();
    loadVersion();
    
    // Initialize i18n
    if (typeof i18n !== 'undefined') {
        await i18n.init();
        
        // Set dropdown to current language
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.value = i18n.getLanguage();
        }
    }
    
    // Add event listener to theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleDarkMode);
    }
    
    // Add event listener to help button
    const helpButton = document.getElementById('help-button');
    if (helpButton) {
        helpButton.addEventListener('click', () => {
            if (typeof keyboard !== 'undefined') {
                keyboard.showHelp();
            }
        });
    }
    
    // Add event listener to language dropdown
    const languageSelect = document.getElementById('language-select');
    if (languageSelect) {
        languageSelect.addEventListener('change', (event) => {
            const lang = event.target.value;
            if (typeof i18n !== 'undefined') {
                i18n.setLanguage(lang);
                toast.success(`✓ ${i18n.getLanguageName(lang)}`);
            }
        });
    }
    
    // Listen for language change events (update dropdown)
    window.addEventListener('languageChanged', (event) => {
        const lang = event.detail.lang;
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.value = lang;
        }
    });
});

let sessionId = null;
let appImageFile = null;
let keyFile = null;

// DOM Elements
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');

const appImageDropZone = document.getElementById('appimage-drop-zone');
const appImageInput = document.getElementById('appimage-input');
const appImageInfo = document.getElementById('appimage-info');

const keyDropZone = document.getElementById('key-drop-zone');
const keyInput = document.getElementById('key-input');
const keyInfo = document.getElementById('key-info');

const keyIdInput = document.getElementById('key-id-input');
const passphraseInput = document.getElementById('passphrase-input');

const signButton = document.getElementById('sign-button');
const progress = document.getElementById('progress');

const resultSuccess = document.getElementById('result-success');
const resultError = document.getElementById('result-error');
const errorMessage = document.getElementById('error-message');
const verificationDetails = document.getElementById('verification-details');

const downloadZip = document.getElementById('download-zip');
const downloadAppImage = document.getElementById('download-appimage');
const downloadSignature = document.getElementById('download-signature');
const resetButton = document.getElementById('reset-button');

// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        const tab = button.dataset.tab;
        
        // Switch active tab button
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        
        // Switch active tab content
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById(`${tab}-tab`).classList.add('active');
    });
});

// Create session on load
async function createSession() {
    try {
        const response = await fetch('/api/session/create', {
            method: 'POST'
        });
        const data = await response.json();
        sessionId = data.session_id;
        console.log('Session created:', sessionId);
    } catch (error) {
        console.error('Failed to create session:', error);
        toast.error('Fehler beim Erstellen der Session. Bitte laden Sie die Seite neu.');
    }
}

// Initialize
createSession();

// AppImage Upload
appImageDropZone.addEventListener('click', () => appImageInput.click());
appImageInput.addEventListener('change', handleAppImageSelect);

appImageDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    appImageDropZone.classList.add('dragover');
});

appImageDropZone.addEventListener('dragleave', () => {
    appImageDropZone.classList.remove('dragover');
});

appImageDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    appImageDropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        appImageInput.files = files;
        handleAppImageSelect({ target: { files: files } });
    }
});

async function handleAppImageSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.AppImage')) {
        toast.warning('Bitte wählen Sie eine .AppImage Datei aus.');
        return;
    }
    
    appImageFile = file;
    
    // Show file info
    appImageInfo.querySelector('.filename').textContent = file.name;
    appImageInfo.querySelector('.filesize').textContent = formatFileSize(file.size);
    appImageInfo.style.display = 'flex';
    
    // Upload file
    await uploadAppImage(file);
}

function uploadAppImageWithProgress(file) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('file', file);
        
        const xhr = new XMLHttpRequest();
        
        // Progress tracking variables
        let startTime = Date.now();
        let lastLoaded = 0;
        let lastTime = startTime;
        
        // Progress event
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const now = Date.now();
                const elapsed = (now - lastTime) / 1000; // seconds
                const currentLoaded = e.loaded;
                const bytesInInterval = currentLoaded - lastLoaded;
                
                // Calculate speed (MB/s)
                const speed = (bytesInInterval / elapsed) / (1024 * 1024);
                
                // Calculate percentage
                const percent = Math.round((e.loaded / e.total) * 100);
                
                // Calculate remaining time
                const remainingBytes = e.total - e.loaded;
                const remainingSeconds = speed > 0 ? remainingBytes / (speed * 1024 * 1024) : 0;
                
                // Update progress display
                updateUploadProgress(percent, speed, remainingSeconds, e.loaded, e.total);
                
                // Update tracking variables
                lastLoaded = currentLoaded;
                lastTime = now;
            }
        });
        
        // Load event (upload complete)
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    resolve(data);
                } catch (error) {
                    reject(new Error('Invalid JSON response'));
                }
            } else {
                try {
                    const error = JSON.parse(xhr.responseText);
                    reject(new Error(error.detail || 'Upload failed'));
                } catch {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            }
        });
        
        // Error event
        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });
        
        // Abort event
        xhr.addEventListener('abort', () => {
            reject(new Error('Upload cancelled'));
        });
        
        // Open and send request
        xhr.open('POST', '/api/upload/appimage');
        xhr.send(formData);
    });
}

function updateUploadProgress(percent, speed, remainingSeconds, loaded, total) {
    // Format file sizes
    const loadedMB = (loaded / (1024 * 1024)).toFixed(2);
    const totalMB = (total / (1024 * 1024)).toFixed(2);
    
    // Format remaining time
    let timeString = '';
    if (remainingSeconds < 60) {
        timeString = `${Math.ceil(remainingSeconds)}s verbleibend`;
    } else {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = Math.ceil(remainingSeconds % 60);
        timeString = `${minutes}m ${seconds}s verbleibend`;
    }
    
    // Update or create progress display
    let progressDiv = document.getElementById('upload-progress');
    if (!progressDiv) {
        progressDiv = document.createElement('div');
        progressDiv.id = 'upload-progress';
        progressDiv.className = 'upload-progress';
        appImageDropZone.appendChild(progressDiv);
    }
    
    progressDiv.innerHTML = `
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${percent}%"></div>
        </div>
        <div class="progress-stats">
            <span class="progress-percent">${percent}%</span>
            <span class="progress-speed">${speed.toFixed(2)} MB/s</span>
            <span class="progress-time">${timeString}</span>
        </div>
        <div class="progress-size">${loadedMB} MB / ${totalMB} MB</div>
    `;
    
    // Hide progress when complete
    if (percent >= 100) {
        setTimeout(() => {
            progressDiv.style.display = 'none';
        }, 2000);
    }
}

async function uploadAppImage(file) {
    try {
        const data = await uploadAppImageWithProgress(file);
        
        console.log('✓ AppImage uploaded successfully');
        console.log('Response data:', data);
        
        // Show signature info if present (without verification)
        if (data.signature_info && data.signature_info.has_signature) {
            console.log('📝 Signature found:', data.signature_info);
            
            displaySignatureInfo('original-signature', data.signature_info);
            document.getElementById('original-signature').style.display = 'block';
            
            // Show verify button
            const verifyButton = document.getElementById('verify-signature-button');
            verifyButton.style.display = 'inline-flex';
            verifyButton.onclick = () => verifyUploadedSignature();
            
            // Add pulse animation after a short delay
            setTimeout(() => {
                verifyButton.classList.add('pulse');
            }, 500);
        } else {
            // No signature found
            console.log('❌ No signature found');
            document.getElementById('signature-upload-hint').style.display = 'block';
        }
        
        // Show success toast
        toast.success('✓ AppImage erfolgreich hochgeladen!');
        
        enableStep(step2);
        checkReadyToSign();
    } catch (error) {
        console.error('Upload error:', error);
        toast.error('Upload fehlgeschlagen: ' + error.message);
    }
}

async function uploadAppImageOLD(file) {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload/appimage', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('✓ AppImage uploaded successfully');
            console.log('Response data:', data);
            
            // Show signature info if present (without verification)
            if (data.signature_info && data.signature_info.has_signature) {
                console.log('📝 Signature found:', data.signature_info);
                
                displaySignatureInfo('original-signature', data.signature_info);
                document.getElementById('original-signature').style.display = 'block';
                
                // Show verify button
                const verifyButton = document.getElementById('verify-signature-button');
                verifyButton.style.display = 'inline-flex';
                verifyButton.onclick = () => verifyUploadedSignature();
                
                // Add pulse animation after a short delay
                setTimeout(() => {
                    verifyButton.classList.add('pulse');
                }, 500);
            } else {
                // No signature found
                console.log('❌ No signature found');
                document.getElementById('signature-upload-hint').style.display = 'block';
            }
            
            enableStep(step2);
            checkReadyToSign();
        } else {
            toast.error('Upload fehlgeschlagen: ' + data.detail);
        }
    } catch (error) {
        console.error('Upload error:', error);
        toast.error('Upload fehlgeschlagen. Bitte versuchen Sie es erneut.');
    }
}

// Signature upload
const signatureInput = document.getElementById('signature-input');
const uploadSignatureLink = document.getElementById('upload-signature-link');

if (uploadSignatureLink) {
    uploadSignatureLink.addEventListener('click', (e) => {
        e.preventDefault();
        signatureInput.click();
    });
}

if (signatureInput) {
    signatureInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/upload/signature', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.verification) {
                displaySignature('original-signature', data.verification, 'Aktuelle Signatur:');
                document.getElementById('original-signature').style.display = 'block';
                document.getElementById('signature-upload-hint').style.display = 'none';
            }
        } catch (error) {
            console.error('Signature upload error:', error);
        }
    });
}

// Key Upload
keyDropZone.addEventListener('click', () => keyInput.click());
keyInput.addEventListener('change', handleKeySelect);

keyDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    keyDropZone.classList.add('dragover');
});

keyDropZone.addEventListener('dragleave', () => {
    keyDropZone.classList.remove('dragover');
});

keyDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    keyDropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        keyInput.files = files;
        handleKeySelect({ target: { files: files } });
    }
});

async function handleKeySelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    keyFile = file;
    
    // Show file info
    keyInfo.querySelector('.filename').textContent = file.name;
    keyInfo.style.display = 'flex';
    
    // Upload file
    await uploadKey(file);
}

async function uploadKey(file) {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload/key', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            console.log('Key uploaded');
            toast.success('✓ GPG-Schlüssel erfolgreich hochgeladen!');
            checkReadyToSign();
        } else {
            const error = await response.json();
            toast.error('Key-Upload fehlgeschlagen: ' + error.detail);
        }
    } catch (error) {
        console.error('Key upload error:', error);
        toast.error('Key-Upload fehlgeschlagen. Bitte versuchen Sie es erneut.');
    }
}

// Check if ready to sign
keyIdInput.addEventListener('input', checkReadyToSign);

function checkReadyToSign() {
    const hasAppImage = appImageFile !== null;
    const hasKey = keyFile !== null || keyIdInput.value.trim() !== '';
    
    if (hasAppImage && hasKey) {
        enableStep(step3);
    }
}

// Sign button
signButton.addEventListener('click', signAppImage);

async function signAppImage() {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    
    const keyId = keyIdInput.value.trim();
    if (keyId) {
        formData.append('key_id', keyId);
    }
    
    const passphrase = passphraseInput.value;
    if (passphrase) {
        formData.append('passphrase', passphrase);
    }
    
    const embedSignature = document.getElementById('embed-signature').checked;
    formData.append('embed_signature', embedSignature);
    
    signButton.disabled = true;
    progress.style.display = 'block';
    
    try {
        const response = await fetch('/api/sign', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(data);
        } else {
            showError(data.detail || 'Signierung fehlgeschlagen');
        }
    } catch (error) {
        console.error('Signing error:', error);
        showError('Signierung fehlgeschlagen: ' + error.message);
    } finally {
        progress.style.display = 'none';
        signButton.disabled = false;
    }
}

function showSuccess(data) {
    step4.style.display = 'block';
    resultSuccess.style.display = 'block';
    resultError.style.display = 'none';
    
    // Show success toast
    toast.success('✓ AppImage erfolgreich signiert!', 6000);
    
    // Show verification details
    const verification = data.verification;
    console.log('Verification data:', verification);
    
    if (verification) {
        if (verification.valid) {
            verificationDetails.innerHTML = `
                <h4>✓ Signatur gültig</h4>
                <dl>
                    <dt>Signiert von:</dt>
                    <dd>${verification.username || 'Unknown'}</dd>
                    
                    <dt>Key ID:</dt>
                    <dd>${verification.key_id}</dd>
                    
                    <dt>Fingerprint:</dt>
                    <dd>${verification.fingerprint || 'N/A'}</dd>
                    
                    <dt>Vertrauensstufe:</dt>
                    <dd>${verification.trust_level || 'Unknown'}</dd>
                    
                    <dt>Zeitstempel:</dt>
                    <dd>${verification.timestamp ? new Date(verification.timestamp * 1000).toLocaleString('de-DE') : 'N/A'}</dd>
                    
                    ${verification.embedded ? '<dt>Typ:</dt><dd>Eingebettete Signatur ✓</dd>' : '<dt>Typ:</dt><dd>Externe .asc Datei</dd>'}
                </dl>
            `;
        } else {
            verificationDetails.innerHTML = `
                <h4 style="color: #dc3545;">⚠ Signatur erstellt, aber Verifikation ausstehend</h4>
                <p>Die Signatur wurde erfolgreich erstellt. Die Verifikation kann fehlschlagen, wenn der öffentliche Schlüssel nicht im Keyring verfügbar ist.</p>
                ${verification.error ? `<p><small>Details: ${verification.error}</small></p>` : ''}
            `;
        }
    } else {
        verificationDetails.innerHTML = `
            <h4 style="color: #ffc107;">ℹ Signatur erstellt</h4>
            <p>Die Signatur wurde erfolgreich erstellt. Verifikationsinformationen sind nicht verfügbar.</p>
        `;
    }
    
    // Set download links
    downloadZip.href = `/api/download/zip/${sessionId}`;
    downloadAppImage.href = data.download_urls.appimage;
    downloadSignature.href = data.download_urls.signature;
    
    // Scroll to result
    step4.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    step4.style.display = 'block';
    resultSuccess.style.display = 'none';
    resultError.style.display = 'block';
    errorMessage.textContent = message;
    
    // Scroll to result
    step4.scrollIntoView({ behavior: 'smooth' });
}

// Reset button
resetButton.addEventListener('click', () => {
    location.reload();
});

// Helper functions
function enableStep(step) {
    step.style.opacity = '1';
    step.style.pointerEvents = 'auto';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function displaySignature(elementId, verification, title) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    let cssClass = '';
    let statusIcon = '';
    
    if (verification.valid) {
        cssClass = 'signature-valid';
        statusIcon = '✅';
    } else if (verification.has_signature === false) {
        cssClass = 'signature-invalid';
        statusIcon = '⚠️';
    } else {
        cssClass = 'signature-invalid';
        statusIcon = '❌';
    }
    
    element.className = `signature-info ${cssClass}`;
    
    const content = document.getElementById(`${elementId}-content`) || element;
    
    if (verification.valid) {
        const sigType = verification.has_signature ? '📦 Eingebettete Signatur' : '📄 Externe Signatur';
        
        content.innerHTML = `
            <h4>${statusIcon} ${title}</h4>
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 15px;">
                ${sigType}
            </p>
            <dl>
                <dt>Signiert von:</dt>
                <dd>${verification.username || 'Unknown'}</dd>
                
                <dt>Key ID:</dt>
                <dd>${verification.key_id || 'N/A'}</dd>
                
                <dt>Fingerprint:</dt>
                <dd>${verification.fingerprint || 'N/A'}</dd>
                
                <dt>Vertrauensstufe:</dt>
                <dd>${verification.trust_level || 'Unknown'}</dd>
                
                <dt>Zeitstempel:</dt>
                <dd>${verification.timestamp ? new Date(verification.timestamp * 1000).toLocaleString('de-DE') : 'N/A'}</dd>
            </dl>
        `;
    } else if (verification.has_signature === false) {
        // No signature found at all
        content.innerHTML = `
            <h4>${statusIcon} ${title}</h4>
            <p style="color: #856404; margin: 10px 0;">Keine Signatur gefunden</p>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 10px;">
                <em>Diese AppImage hat weder eine eingebettete Signatur noch eine externe .asc-Datei. 
                Sie können eine neue Signatur erstellen, indem Sie unten einen GPG-Key hochladen.</em>
            </p>
        `;
    } else {
        // Invalid signature
        const errorMsg = verification.error || 'Signatur ungültig';
        const keyInfo = verification.key_id ? `<p><small>Key ID: ${verification.key_id}</small></p>` : '';
        
        content.innerHTML = `
            <h4>${statusIcon} ${title}</h4>
            <p style="color: #721c24; margin: 10px 0;">${errorMsg}</p>
            ${keyInfo}
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 10px;">
                <em>Die Signatur konnte nicht verifiziert werden. Möglicherweise fehlt der öffentliche Schlüssel oder die Signatur ist beschädigt.</em>
            </p>
        `;
    }
}

function displaySignatureInfo(elementId, signatureInfo) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const content = document.getElementById(`${elementId}-content`) || element;
    
    if (signatureInfo.has_signature) {
        const sigTypeIcon = signatureInfo.type === 'embedded' ? '📦' : '📄';
        const sigTypeName = signatureInfo.type === 'embedded' ? 'Eingebettete Signatur' : 'Externe Signatur (.asc)';
        
        // Build metadata section if available
        let metadataHtml = '';
        if (signatureInfo.metadata && signatureInfo.metadata.raw_available) {
            const meta = signatureInfo.metadata;
            
            metadataHtml = `
                <div class="signature-live-preview">
                    <h5 style="margin: 15px 0 10px 0; font-size: 14px; color: var(--text-primary);">
                        ✨ Live-Analyse der Signatur:
                    </h5>
                    <div class="metadata-grid">
                        ${meta.algorithm ? `
                        <div class="metadata-item">
                            <span class="metadata-label">🔑 Algorithmus:</span>
                            <span class="metadata-value">${meta.algorithm}</span>
                        </div>
                        ` : ''}
                        
                        ${meta.hash_algorithm ? `
                        <div class="metadata-item">
                            <span class="metadata-label">🔒 Hash:</span>
                            <span class="metadata-value">${meta.hash_algorithm}</span>
                        </div>
                        ` : ''}
                        
                        ${meta.version ? `
                        <div class="metadata-item">
                            <span class="metadata-label">📋 Version:</span>
                            <span class="metadata-value">OpenPGP v${meta.version}</span>
                        </div>
                        ` : ''}
                        
                        ${meta.timestamp_readable ? `
                        <div class="metadata-item">
                            <span class="metadata-label">📅 Erstellt:</span>
                            <span class="metadata-value">${meta.timestamp_readable}</span>
                        </div>
                        ` : ''}
                        
                        ${meta.key_id ? `
                        <div class="metadata-item">
                            <span class="metadata-label">🆔 Key ID:</span>
                            <span class="metadata-value" style="font-family: 'Courier New', monospace;">${formatKeyId(meta.key_id)}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    ${meta.parse_error ? `
                    <p style="color: #856404; font-size: 12px; margin-top: 10px;">
                        ⚠️ Teilweise Metadaten: ${meta.parse_error}
                    </p>
                    ` : ''}
                </div>
            `;
        }
        
        content.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span style="font-size: 24px;">${sigTypeIcon}</span>
                <div>
                    <strong>${sigTypeName}</strong>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 5px 0 0 0;">
                        Größe: ${signatureInfo.size} bytes
                    </p>
                </div>
            </div>
            
            ${metadataHtml}
            
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: var(--global--color-ionos-blue); font-size: 14px; font-weight: 600;">
                    📄 Signatur-Rohdaten anzeigen
                </summary>
                <div style="position: relative; margin-top: 10px;">
                    <button onclick="copyToClipboard('${elementId}-signature-raw')" 
                            style="position: absolute; top: 10px; right: 10px; padding: 5px 10px; background: var(--global--color-ionos-blue); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; z-index: 10;">
                        📋 Kopieren
                    </button>
                    <pre id="${elementId}-signature-raw" style="background: var(--upload-zone-bg); padding: 15px 10px 10px 10px; border-radius: 8px; overflow-x: auto; font-size: 11px; margin: 0;">${escapeHtml(signatureInfo.signature_data)}</pre>
                </div>
            </details>
            
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 15px; padding: 12px; background: var(--upload-zone-bg); border-radius: 8px; border-left: 4px solid var(--global--color-ionos-blue);">
                <em>ℹ️ Klicken Sie auf "Signatur verifizieren" um die Gültigkeit mit GPG zu prüfen.</em>
            </p>
        `;
    } else {
        content.innerHTML = `
            <p style="color: #856404; margin: 10px 0;">Keine Signatur gefunden</p>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 10px;">
                <em>Diese AppImage hat weder eine eingebettete Signatur noch eine externe .asc-Datei.</em>
            </p>
        `;
    }
}

// Helper function to format Key ID with spaces
function formatKeyId(keyId) {
    if (!keyId) return '';
    // Add space every 4 characters: A1EA6539514E0105 -> A1EA 6539 514E 0105
    return keyId.match(/.{1,4}/g).join(' ');
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Copy to clipboard function
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const text = element.textContent;
    navigator.clipboard.writeText(text).then(() => {
        // Show temporary feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '✓ Kopiert!';
        button.style.background = '#2ecc71';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = 'var(--global--color-ionos-blue)';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        toast.error('Kopieren fehlgeschlagen. Bitte manuell markieren und kopieren.');
    });
}

async function verifyUploadedSignature() {
    const verifyButton = document.getElementById('verify-signature-button');
    const originalText = verifyButton.innerHTML;
    
    verifyButton.disabled = true;
    verifyButton.innerHTML = '<span class="btn-icon">⏳</span> Verifiziere...';
    
    try {
        const response = await fetch(`/api/verify/uploaded/${sessionId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.verification) {
            // Replace signature info with verification result
            displaySignature('original-signature', data.verification, 'Signatur verifiziert');
            verifyButton.style.display = 'none';
        } else {
            toast.error('Verifikation fehlgeschlagen: ' + (data.detail || 'Unbekannter Fehler'));
            verifyButton.disabled = false;
            verifyButton.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Verification error:', error);
        toast.error('Verifikation fehlgeschlagen: ' + error.message);
        verifyButton.disabled = false;
        verifyButton.innerHTML = originalText;
    }
}
