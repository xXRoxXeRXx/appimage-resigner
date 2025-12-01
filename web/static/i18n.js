/**
 * i18n Configuration and Management
 * Lightweight internationalization without external dependencies
 */

class I18n {
    constructor() {
        this.currentLang = 'de';
        this.translations = {};
        this.fallbackLang = 'de';
        this.initialized = false;
    }

    /**
     * Initialize i18n with translations
     */
    async init() {
        // Load translations
        await this.loadTranslations();
        
        // Get saved language or browser language
        const savedLang = localStorage.getItem('language');
        const browserLang = navigator.language.split('-')[0];
        
        // Set initial language
        this.currentLang = savedLang || (this.translations[browserLang] ? browserLang : this.fallbackLang);
        
        // Apply language
        this.setLanguage(this.currentLang);
        
        this.initialized = true;
        console.log(`🌍 i18n initialized with language: ${this.currentLang}`);
    }

    /**
     * Load translation files
     */
    async loadTranslations() {
        try {
            // Load German translations
            const deResponse = await fetch('/static/locales/de.json');
            this.translations.de = await deResponse.json();
            
            // Load English translations
            const enResponse = await fetch('/static/locales/en.json');
            this.translations.en = await enResponse.json();
            
            console.log('✅ Translations loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load translations:', error);
            // Fallback to embedded translations if fetch fails
            this.loadEmbeddedTranslations();
        }
    }

    /**
     * Fallback embedded translations (in case files can't be loaded)
     */
    loadEmbeddedTranslations() {
        this.translations = {
            de: {
                title: "AppImage Re-Signer",
                subtitle: "Signieren Sie Ihre AppImages einfach über das Web"
            },
            en: {
                title: "AppImage Re-Signer",
                subtitle: "Sign your AppImages easily via the web"
            }
        };
    }

    /**
     * Get translation by key
     * @param {string} key - Translation key (supports nested: 'step1.title')
     * @param {object} params - Optional parameters for interpolation
     */
    t(key, params = {}) {
        if (!this.initialized) {
            console.warn('i18n not initialized yet');
            return key;
        }

        // Get translation from current language
        let translation = this.getNestedValue(this.translations[this.currentLang], key);
        
        // Fallback to fallback language
        if (!translation) {
            translation = this.getNestedValue(this.translations[this.fallbackLang], key);
        }
        
        // Fallback to key itself
        if (!translation) {
            console.warn(`Translation missing for key: ${key}`);
            return key;
        }

        // Interpolate parameters
        return this.interpolate(translation, params);
    }

    /**
     * Get nested value from object using dot notation
     */
    getNestedValue(obj, key) {
        return key.split('.').reduce((o, k) => (o || {})[k], obj);
    }

    /**
     * Interpolate parameters in translation string
     * Example: "Hello {name}!" with {name: 'World'} => "Hello World!"
     */
    interpolate(str, params) {
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    /**
     * Set current language
     */
    setLanguage(lang) {
        if (!this.translations[lang]) {
            console.error(`Language ${lang} not available`);
            return;
        }

        this.currentLang = lang;
        localStorage.setItem('language', lang);
        
        // Update HTML lang attribute
        document.documentElement.lang = lang;
        
        // Trigger language change event
        this.updateUI();
        
        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
        
        console.log(`🌍 Language changed to: ${lang}`);
    }

    /**
     * Update all UI elements with data-i18n attribute
     */
    updateUI() {
        // Update elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });

        // Update elements with data-i18n-placeholder attribute
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = this.t(key);
        });

        // Update elements with data-i18n-title attribute
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = this.t(key);
        });

        // Update elements with data-i18n-html attribute (for HTML content)
        document.querySelectorAll('[data-i18n-html]').forEach(element => {
            const key = element.getAttribute('data-i18n-html');
            element.innerHTML = this.t(key);
        });
    }

    /**
     * Get current language
     */
    getLanguage() {
        return this.currentLang;
    }

    /**
     * Get available languages
     */
    getAvailableLanguages() {
        return Object.keys(this.translations);
    }

    /**
     * Get language name
     */
    getLanguageName(lang) {
        const names = {
            de: 'Deutsch',
            en: 'English'
        };
        return names[lang] || lang;
    }

    /**
     * Get language flag emoji
     */
    getLanguageFlag(lang) {
        const flags = {
            de: '🇩🇪',
            en: '🇬🇧'
        };
        return flags[lang] || '🌍';
    }
}

// Create global i18n instance
const i18n = new I18n();

// Make available globally
window.i18n = i18n;

// Helper function for easy access
window.t = (key, params) => i18n.t(key, params);
