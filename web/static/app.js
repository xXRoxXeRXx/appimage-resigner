// AppImage Re-Signer - Frontend Logic

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
        alert('Fehler beim Erstellen der Session');
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
        alert('Bitte wählen Sie eine .AppImage Datei');
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

async function uploadAppImage(file) {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload/appimage', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            console.log('AppImage uploaded');
            enableStep(step2);
            checkReadyToSign();
        } else {
            const error = await response.json();
            alert('Upload fehlgeschlagen: ' + error.detail);
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload fehlgeschlagen');
    }
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
            checkReadyToSign();
        } else {
            const error = await response.json();
            alert('Key-Upload fehlgeschlagen: ' + error.detail);
        }
    } catch (error) {
        console.error('Key upload error:', error);
        alert('Key-Upload fehlgeschlagen');
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
    
    // Show verification details
    const verification = data.verification;
    if (verification && verification.valid) {
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
            </dl>
        `;
    }
    
    // Set download links
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
