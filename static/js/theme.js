// Theme toggle - claro/escuro
// Fase 1: aplica classe 'dark' o mais cedo possível (pode rodar no <head>)
(function() {
    const html = document.documentElement;
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved ? saved === 'dark' : prefersDark;
    if (isDark) {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
})();

// Fase 2: toggle button + ícones (precisa do DOM carregado)
document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('theme-toggle');
    const iconLight = document.getElementById('theme-icon-light');
    const iconDark = document.getElementById('theme-icon-dark');
    const html = document.documentElement;

    function applyTheme(dark) {
        if (dark) {
            html.classList.add('dark');
            if (iconLight) iconLight.classList.remove('hidden');
            if (iconDark) iconDark.classList.add('hidden');
        } else {
            html.classList.remove('dark');
            if (iconLight) iconLight.classList.add('hidden');
            if (iconDark) iconDark.classList.remove('hidden');
        }
    }

    // Sincronizar ícones com o estado atual
    applyTheme(html.classList.contains('dark'));

    if (toggle) {
        toggle.addEventListener('click', function() {
            const nowDark = !html.classList.contains('dark');
            applyTheme(nowDark);
            localStorage.setItem('theme', nowDark ? 'dark' : 'light');
        });
    }
});
