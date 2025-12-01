/**
 * Keyboard Shortcuts Manager
 * Handles all keyboard shortcuts for the AppImage Re-Signer web interface
 */

class KeyboardManager {
    constructor() {
        this.shortcuts = new Map();
        this.enabled = true;
        this.init();
    }

    init() {
        // Register global keyboard event listener
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Register default shortcuts
        this.registerDefaultShortcuts();
        
        console.log('🎹 Keyboard shortcuts initialized');
    }

    /**
     * Register a keyboard shortcut
     * @param {string} key - Key combination (e.g., 'Escape', 'ctrl+s', 'Enter')
     * @param {Function} handler - Handler function
     * @param {string} description - Description for help text
     * @param {string} context - Context where shortcut is active (optional)
     */
    register(key, handler, description, context = 'global') {
        const normalizedKey = this.normalizeKey(key);
        
        if (!this.shortcuts.has(context)) {
            this.shortcuts.set(context, new Map());
        }
        
        this.shortcuts.get(context).set(normalizedKey, {
            handler,
            description,
            key: normalizedKey
        });
    }

    /**
     * Normalize key combinations for consistent matching
     */
    normalizeKey(key) {
        return key.toLowerCase()
            .replace('control', 'ctrl')
            .replace('command', 'meta')
            .replace('option', 'alt');
    }

    /**
     * Handle keydown events
     */
    handleKeyDown(e) {
        if (!this.enabled) return;

        // Build key combination string
        let keyCombination = '';
        
        if (e.ctrlKey || e.metaKey) keyCombination += 'ctrl+';
        if (e.altKey) keyCombination += 'alt+';
        if (e.shiftKey && !['Shift'].includes(e.key)) keyCombination += 'shift+';
        
        keyCombination += e.key.toLowerCase();

        // Check if we should ignore this key (typing in input)
        if (this.shouldIgnoreKey(e)) {
            return;
        }

        // Try to find and execute handler
        const executed = this.executeShortcut(keyCombination, e);
        
        if (executed) {
            e.preventDefault();
            e.stopPropagation();
        }
    }

    /**
     * Check if we should ignore the key event (e.g., typing in input field)
     */
    shouldIgnoreKey(e) {
        const target = e.target;
        const tagName = target.tagName.toLowerCase();
        
        // Allow ESC even in inputs
        if (e.key === 'Escape') return false;
        
        // Allow Ctrl/Cmd combinations even in inputs
        if (e.ctrlKey || e.metaKey) return false;
        
        // Ignore if typing in input fields
        return ['input', 'textarea', 'select'].includes(tagName) && 
               !['Escape', 'Enter'].includes(e.key);
    }

    /**
     * Execute a shortcut if found
     */
    executeShortcut(keyCombination, event) {
        // Try global shortcuts first
        if (this.shortcuts.has('global')) {
            const globalShortcuts = this.shortcuts.get('global');
            if (globalShortcuts.has(keyCombination)) {
                globalShortcuts.get(keyCombination).handler(event);
                return true;
            }
        }
        
        return false;
    }

    /**
     * Register all default shortcuts
     */
    registerDefaultShortcuts() {
        // ESC - Close/Cancel/Reset
        this.register('escape', (e) => {
            // Clear file selection if on step 1
            const appimageInfo = document.getElementById('appimage-info');
            const keyInfo = document.getElementById('key-info');
            
            if (appimageInfo && appimageInfo.style.display !== 'none') {
                // Reset AppImage selection
                const appimageInput = document.getElementById('appimage-input');
                if (appimageInput) appimageInput.value = '';
                appimageInfo.style.display = 'none';
                toast.info('AppImage-Auswahl zurückgesetzt');
                return;
            }
            
            if (keyInfo && keyInfo.style.display !== 'none') {
                // Reset Key selection
                const keyInput = document.getElementById('key-input');
                if (keyInput) keyInput.value = '';
                keyInfo.style.display = 'none';
                toast.info('Schlüssel-Auswahl zurückgesetzt');
                return;
            }
            
            // Blur active element (unfocus)
            if (document.activeElement) {
                document.activeElement.blur();
            }
        }, 'Auswahl zurücksetzen / Unfokussieren');

        // Enter - Submit/Continue based on context
        this.register('enter', (e) => {
            const target = e.target;
            
            // If in passphrase field and sign button is enabled, trigger sign
            if (target.id === 'passphrase-input') {
                const signButton = document.getElementById('sign-button');
                if (signButton && !signButton.disabled) {
                    signButton.click();
                }
                return;
            }
            
            // If sign button is focused, click it
            if (target.id === 'sign-button') {
                target.click();
            }
        }, 'Formular absenden / Signieren');

        // Ctrl+S - Trigger signing (if ready)
        this.register('ctrl+s', (e) => {
            const signButton = document.getElementById('sign-button');
            if (signButton && !signButton.disabled) {
                signButton.click();
                toast.info('🔐 Signierung gestartet...');
            } else {
                toast.warning('Bitte laden Sie zuerst AppImage und GPG-Schlüssel hoch');
            }
        }, 'AppImage signieren');

        // Ctrl+D - Download result (if available)
        this.register('ctrl+d', (e) => {
            const downloadZip = document.getElementById('download-zip');
            if (downloadZip && downloadZip.href !== '#') {
                downloadZip.click();
                toast.info('⬇️ Download gestartet...');
            }
        }, 'Ergebnis herunterladen');

        // Ctrl+R - Reset/New signing
        this.register('ctrl+r', (e) => {
            const step4 = document.getElementById('step4');
            if (step4 && step4.style.display !== 'none') {
                // Reload page to start fresh
                if (confirm('Neue Signierung starten? Die aktuelle Sitzung wird zurückgesetzt.')) {
                    window.location.reload();
                }
            }
        }, 'Neue Signierung starten');

        // Ctrl+H - Show keyboard shortcuts help
        this.register('ctrl+h', (e) => {
            this.showHelp();
        }, 'Tastaturkürzel anzeigen');

        // Ctrl+T - Toggle dark/light theme
        this.register('ctrl+t', (e) => {
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.click();
            }
        }, 'Dark/Light Mode wechseln');

        // F1 - Show help
        this.register('f1', (e) => {
            this.showHelp();
        }, 'Hilfe anzeigen');
    }

    /**
     * Show keyboard shortcuts help
     */
    showHelp() {
        // Use i18n if available, otherwise fallback to German
        const t = (key) => (typeof i18n !== 'undefined' && i18n.initialized) ? i18n.t(key) : key;
        
        let helpText = t('keyboard.help') + '\n\n';
        
        if (this.shortcuts.has('global')) {
            this.shortcuts.get('global').forEach((shortcut, key) => {
                const displayKey = key
                    .replace('ctrl+', 'Strg+')
                    .replace('alt+', 'Alt+')
                    .replace('shift+', 'Shift+')
                    .toUpperCase();
                helpText += `${displayKey}: ${shortcut.description}\n`;
            });
        }
        
        helpText += '\n' + t('keyboard.tip');
        
        // Use toast with longer duration for help
        toast.info(helpText, 15000);
    }

    /**
     * Enable keyboard shortcuts
     */
    enable() {
        this.enabled = true;
        console.log('🎹 Keyboard shortcuts enabled');
    }

    /**
     * Disable keyboard shortcuts
     */
    disable() {
        this.enabled = false;
        console.log('🎹 Keyboard shortcuts disabled');
    }

    /**
     * Get all registered shortcuts
     */
    getShortcuts() {
        return Array.from(this.shortcuts.entries()).flatMap(([context, shortcuts]) =>
            Array.from(shortcuts.entries()).map(([key, data]) => ({
                context,
                key,
                ...data
            }))
        );
    }
}

// Initialize global keyboard manager
const keyboard = new KeyboardManager();

// Make available globally for debugging
window.keyboard = keyboard;
