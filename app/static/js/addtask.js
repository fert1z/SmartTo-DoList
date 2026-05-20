// Добавление задачи через POST /tasks/new

document.addEventListener('DOMContentLoaded', function () {
    const addTaskForm = document.getElementById('add-task-form');
    if (addTaskForm) {
        addTaskForm.addEventListener('submit', function (e) {
            e.preventDefault();
            handleAddTask();
        });
    }

    const voiceTaskBtn = document.getElementById('voice-task');
    if (voiceTaskBtn) {
        voiceTaskBtn.addEventListener('click', function () {
            startVoiceRecording();
        });
    }
});

function showFormMessage(text, isError) {
    const el = document.getElementById('addtask-message');
    if (!el) {
        alert(text);
        return;
    }
    el.textContent = text;
    el.className = 'addtask-message ' + (isError ? 'addtask-message--error' : 'addtask-message--ok');
    el.hidden = false;
}

function handleAddTask() {
    const title = (document.getElementById('task-title') || {}).value || '';
    const description = (document.getElementById('task-description') || {}).value || '';
    const datetime = (document.getElementById('task-datetime') || {}).value || '';
    const priorityEl = document.getElementById('task-priority');
    const priority = priorityEl ? priorityEl.value : 'medium';
    const categoryEl = document.getElementById('task-category');
    const category = categoryEl ? categoryEl.value : 'personal';

    if (!title.trim()) {
        showFormMessage('Введите название задачи.', true);
        return;
    }

    if (datetime) {
        const selected = new Date(datetime);
        const now = new Date();
        if (!isNaN(selected.getTime()) && selected <= now) {
            showFormMessage('Укажите дату и время в будущем или оставьте поле пустым.', true);
            return;
        }
    }

    const params = new URLSearchParams({
        title: title.trim(),
        description: description,
        priority: priority,
        category: category,
    });
    if (datetime) {
        params.set('task-datetime', datetime);
    }

    fetch('/api/tasks', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params,
    })
        .then(function (response) {
            if (response.status === 401) {
                window.location.href = '/auth/login';
                return null;
            }
            return response.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.success) {
                showFormMessage('Задача сохранена. Переход на список…', false);
                setTimeout(function () {
                    window.location.href = '/dashboard';
                }, 600);
                return;
            }
            showFormMessage(data.error || 'Не удалось сохранить задачу', true);
        })
        .catch(function (err) {
            console.error(err);
            showFormMessage('Ошибка сети. Попробуйте ещё раз.', true);
        });
}

function startVoiceRecording() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        showFormMessage('Браузер не поддерживает распознавание речи. Используйте Chrome или Edge.', true);
        return;
    }

    var btn = document.getElementById('voice-task');
    var originalText = btn.value;
    btn.value = '🎤 Слушаю…';
    btn.disabled = true;

    function restore() {
        btn.value = originalText;
        btn.disabled = false;
    }

    function micNotAllowed() {
        restore();
        showFormMessage(
            'Доступ к микрофону запрещён. Разрешите микрофон в настройках браузера (иконка слева от адреса) и повторите диктовку.',
            true
        );
    }

    var recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function (event) {
        var transcript = event.results[0][0].transcript;
        var titleInput = document.getElementById('task-title');
        if (titleInput) titleInput.value = transcript;
        showFormMessage('Текст вставлен в название. При необходимости отредактируйте и нажмите «Сохранить».', false);
    };

    recognition.onerror = function (event) {
        if (event && event.error === 'not-allowed') {
            micNotAllowed();
            return;
        }
        restore();
        showFormMessage('Ошибка микрофона: ' + (event && event.error ? event.error : 'unknown'), true);
    };

    recognition.onend = function () {
        restore();
    };

    // Попробуем заранее запросить доступ к микрофону, чтобы браузер показал permission prompt.
    try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices
                .getUserMedia({ audio: true })
                .then(function (stream) {
                    // Отпускаем поток сразу, т.к. SpeechRecognition сам управляет устройством.
                    try {
                        stream.getTracks().forEach(function (t) {
                            t.stop();
                        });
                    } catch (e) {
                        // ignore
                    }
                    recognition.start();
                })
                .catch(function (err) {
                    if (err && err.name === 'NotAllowedError') {
                        micNotAllowed();
                        return;
                    }
                    restore();
                    showFormMessage('Не удалось получить доступ к микрофону. Проверьте настройки браузера.', true);
                });
        } else {
            recognition.start();
        }
    } catch (e) {
        restore();
        showFormMessage('Не удалось запустить запись.', true);
    }
}
