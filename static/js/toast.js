/*!
 * Opium — Sistema de alertas / toasts profesional
 * Reemplaza a alert() con notificaciones no intrusivas, accesibles y con auto-dismiss.
 * API global: window.OpiumToast.success/error/warning/info(msg, opts?)
 *             window.OpiumToast.show({title, message, type, duration})
 */
(function () {
    'use strict';
    if (window.OpiumToast) return;

    const ICONS = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
        error:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    const TITLES = {
        success: 'Listo',
        error:   'Error',
        warning: 'Aviso',
        info:    'Información'
    };

    function ensureContainer() {
        let el = document.getElementById('opium-toast-container');
        if (el) return el;
        el = document.createElement('div');
        el.id = 'opium-toast-container';
        el.className = 'toast-container';
        el.setAttribute('role', 'region');
        el.setAttribute('aria-label', 'Notificaciones');
        el.setAttribute('aria-live', 'polite');
        document.body.appendChild(el);
        return el;
    }

    function escapeText(s) {
        const d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function show(opts) {
        const container = ensureContainer();
        const type = ['success', 'error', 'warning', 'info'].includes(opts.type) ? opts.type : 'info';
        const title = opts.title || TITLES[type];
        const message = opts.message || '';
        const duration = typeof opts.duration === 'number' ? opts.duration : (type === 'error' ? 7000 : 5000);

        const toast = document.createElement('div');
        toast.className = 'toast toast--' + type;
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
        toast.style.setProperty('--toast-duration', duration + 'ms');

        toast.innerHTML =
            '<span class="toast-icon" aria-hidden="true">' + ICONS[type] + '</span>' +
            '<div class="toast-body">' +
                '<span class="toast-title">' + escapeText(title) + '</span>' +
                '<span class="toast-msg">' + escapeText(message) + '</span>' +
            '</div>' +
            '<button type="button" class="toast-close" aria-label="Cerrar notificación">&times;</button>';

        function dismiss() {
            if (toast.classList.contains('leaving')) return;
            toast.classList.add('leaving');
            setTimeout(() => toast.remove(), 320);
        }

        toast.querySelector('.toast-close').addEventListener('click', dismiss);
        if (duration > 0) setTimeout(dismiss, duration);

        container.appendChild(toast);
        return { dismiss };
    }

    const API = {
        show,
        success: (message, opts) => show(Object.assign({}, opts, { type: 'success', message })),
        error:   (message, opts) => show(Object.assign({}, opts, { type: 'error',   message })),
        warning: (message, opts) => show(Object.assign({}, opts, { type: 'warning', message })),
        info:    (message, opts) => show(Object.assign({}, opts, { type: 'info',    message })),
    };

    window.OpiumToast = API;
})();
