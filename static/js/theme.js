// Theme toggle - claro/escuro
(function() {
    const toggle = document.getElementById('theme-toggle');
    const iconLight = document.getElementById('theme-icon-light');
    const iconDark = document.getElementById('theme-icon-dark');
    const html = document.documentElement;

    function applyTheme(dark) {
        if (dark) {
            html.classList.add('dark');
            iconLight.classList.remove('hidden');
            iconDark.classList.add('hidden');
        } else {
            html.classList.remove('dark');
            iconLight.classList.add('hidden');
            iconDark.classList.remove('hidden');
        }
    }

    // Load saved preference or use system preference
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved ? saved === 'dark' : prefersDark;
    applyTheme(isDark);

    if (toggle) {
        toggle.addEventListener('click', function() {
            const nowDark = !html.classList.contains('dark');
            applyTheme(nowDark);
            localStorage.setItem('theme', nowDark ? 'dark' : 'light');
        });
    }
})();
