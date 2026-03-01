// Theme toggle - claro/escuro
// Fase 1: aplica classe 'dark' o mais cedo possível (roda no <head>)
(function() {
    var html = document.documentElement;
    var saved = localStorage.getItem('theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var isDark = saved ? saved === 'dark' : prefersDark;
    if (isDark) {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
})();

// Fase 2: sincronizar ícones com o estado atual (precisa do DOM)
document.addEventListener('DOMContentLoaded', function() {
    var isDark = document.documentElement.classList.contains('dark');
    var iconLight = document.getElementById('theme-icon-light');
    var iconDark = document.getElementById('theme-icon-dark');
    if (isDark) {
        if (iconLight) iconLight.classList.remove('hidden');
        if (iconDark) iconDark.classList.add('hidden');
    } else {
        if (iconLight) iconLight.classList.add('hidden');
        if (iconDark) iconDark.classList.remove('hidden');
    }
});
