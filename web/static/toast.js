/**
 * Toast Notification System
 * Modern replacement for alert() and confirm()
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in milliseconds (0 = no auto-dismiss)
     * @returns {HTMLElement} The toast element
     */
    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} toast-enter`;
        
        // Icon based on type
        const icons = {
            success: '✓',
            error: '✕',
            info: 'ℹ',
            warning: '⚠'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" aria-label="Close">&times;</button>
        `;

        // Add to container
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Trigger animation
        setTimeout(() => {
            toast.classList.remove('toast-enter');
        }, 10);

        // Close button
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.hide(toast));

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                this.hide(toast);
            }, duration);
        }

        return toast;
    }

    /**
     * Hide a toast notification
     * @param {HTMLElement} toast - The toast element to hide
     */
    hide(toast) {
        if (!toast || !toast.parentNode) return;

        toast.classList.add('toast-exit');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300);
    }

    /**
     * Hide all toasts
     */
    hideAll() {
        this.toasts.forEach(toast => this.hide(toast));
    }

    // Convenience methods
    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 7000) {
        return this.show(message, 'error', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    /**
     * Show a confirmation toast (replaces confirm())
     * @param {string} message - The confirmation message
     * @param {Function} onConfirm - Callback when confirmed
     * @param {Function} onCancel - Callback when cancelled
     */
    confirm(message, onConfirm, onCancel = null) {
        const toast = document.createElement('div');
        toast.className = 'toast toast-confirm toast-enter';
        
        toast.innerHTML = `
            <div class="toast-icon">?</div>
            <div class="toast-message">${message}</div>
            <div class="toast-actions">
                <button class="toast-btn toast-btn-confirm">Ja</button>
                <button class="toast-btn toast-btn-cancel">Nein</button>
            </div>
        `;

        this.container.appendChild(toast);
        this.toasts.push(toast);

        setTimeout(() => {
            toast.classList.remove('toast-enter');
        }, 10);

        // Confirm button
        const confirmBtn = toast.querySelector('.toast-btn-confirm');
        confirmBtn.addEventListener('click', () => {
            this.hide(toast);
            if (onConfirm) onConfirm();
        });

        // Cancel button
        const cancelBtn = toast.querySelector('.toast-btn-cancel');
        cancelBtn.addEventListener('click', () => {
            this.hide(toast);
            if (onCancel) onCancel();
        });

        return toast;
    }
}

// Create global instance
const toast = new ToastManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ToastManager, toast };
}
