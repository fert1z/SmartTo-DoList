// Глобальный скрипт для управления темами

(function() {
    // Применяем тему немедленно, до полной загрузки DOM
    function applyTheme() {
        var theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            document.documentElement.classList.add('dark-theme');
        } else {
            document.documentElement.classList.remove('dark-theme');
        }
    }

    applyTheme();

    // Этот код будет выполнен после загрузки страницы
    document.addEventListener('DOMContentLoaded', function() {
        var themeSwitcher = document.getElementById('theme-switcher');

        if (themeSwitcher) {
            var currentTheme = localStorage.getItem('theme') || 'light';
            themeSwitcher.value = currentTheme;

            themeSwitcher.addEventListener('change', function(e) {
                var newTheme = e.target.value;
                localStorage.setItem('theme', newTheme);
                
                // Переключаем класс на корневом элементе <html>
                if (newTheme === 'dark') {
                    document.documentElement.classList.add('dark-theme');
                } else {
                    document.documentElement.classList.remove('dark-theme');
                }
            });
        }
    });
})();