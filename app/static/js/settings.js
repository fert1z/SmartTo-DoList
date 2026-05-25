(function() {
    var csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        console.warn('CSRF token not available on settings page');
        return;
    }

    var settingsForm = document.querySelector('.settings-form');
    var btnCode = document.getElementById('btn-telegram-code');
    var btnUnlink = document.getElementById('btn-telegram-unlink');
    var box = document.getElementById('telegram-code-box');
    var val = document.getElementById('telegram-code-value');
    var msg = document.getElementById('telegram-msg');

    // Перехват отправки формы настроек
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(settingsForm);
            var data = Object.fromEntries(formData.entries());

            fetchJson('/account/edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(function(response) {
                alert(response.message || 'Настройки сохранены!');
                window.location.reload();
            })
            .catch(function(err) {
                alert(err.error || 'Произошла ошибка');
            });
        });
    }

    function fetchJson(url, init) {
        init = init || {};
        init.headers = Object.assign({}, init.headers || {}, {
            'Accept': 'application/json',
            'X-CSRFToken': csrfToken,
        });
        return fetch(url, init).then(function(response) {
            return response.json().then(function(data) {
                if (!response.ok) {
                    return Promise.reject(data);
                }
                return data;
            });
        });
    }

    if (btnCode) {
        btnCode.addEventListener('click', function() {
            if (msg) {
                msg.textContent = '';
            }
            fetchJson('/account/telegram/generate-link', { method: 'POST' })
                .then(function(data) {
                    if (data.error) {
                        if (msg) msg.textContent = data.error;
                        return;
                    }
                    if (val) val.textContent = data.code;
                    if (box) box.hidden = false;
                })
                .catch(function() {
                    if (msg) msg.textContent = 'Не удалось получить код';
                });
        });
    }

    if (btnUnlink) {
        btnUnlink.addEventListener('click', function() {
            if (!confirm('Отвязать Telegram от этого аккаунта?')) return;
            fetchJson('/account/telegram/unlink', { method: 'POST' })
                .then(function(data) {
                    if (data.success) {
                        window.location.reload();
                        return;
                    }
                    alert(data.error || 'Ошибка');
                })
                .catch(function() {
                    alert('Ошибка при отвязке Telegram');
                });
        });
    }
})();