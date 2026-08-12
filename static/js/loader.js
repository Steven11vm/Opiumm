/*!
 * Opium — Controlador de la pantalla de carga.
 * Se asegura de mostrar el loader al menos MIN_TIME ms para evitar flicker,
 * y lo esconde en el evento window.load. Se auto-elimina del DOM.
 */
(function () {
    'use strict';
    var html = document.documentElement;
    html.classList.add('opium-loading');

    document.addEventListener('DOMContentLoaded', function () {
        var loader = document.getElementById('opiumLoader');
        if (!loader) {
            html.classList.remove('opium-loading');
            return;
        }
        var MIN_TIME = 500;
        var MAX_TIME = 6000;
        var start = (window.performance && performance.now) ? performance.now() : Date.now();
        var hidden = false;

        function now() {
            return (window.performance && performance.now) ? performance.now() : Date.now();
        }

        function hide() {
            if (hidden) return;
            hidden = true;
            var elapsed = now() - start;
            var wait = Math.max(0, MIN_TIME - elapsed);
            setTimeout(function () {
                loader.classList.add('is-hidden');
                html.classList.remove('opium-loading');
                setTimeout(function () {
                    if (loader && loader.parentNode) loader.parentNode.removeChild(loader);
                }, 650);
            }, wait);
        }

        if (document.readyState === 'complete') {
            hide();
        } else {
            window.addEventListener('load', hide, { once: true });
        }
        setTimeout(hide, MAX_TIME);
    });
})();
