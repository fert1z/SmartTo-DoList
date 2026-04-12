// Add Task JavaScript - Функции добавления новых задач

document.addEventListener('DOMContentLoaded', function() {
    // Обработка формы добавления задачи
    const addTaskForm = document.getElementById('add-task-form');
    if (addTaskForm) {
        addTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleAddTask();
        });
    }
    
    // Обработка голосовой записи
    const voiceTaskBtn = document.getElementById('voice-task');
    if (voiceTaskBtn) {
        voiceTaskBtn.addEventListener('click', function() {
            startVoiceRecording();
        });
    }
});

// Добавить задачу из формы
function handleAddTask() {
    const title = document.getElementById('task-title').value;
    const description = document.getElementById('task-description').value;
    const datetime = document.getElementById('task-datetime').value;
    
    if (!title.trim()) {
        alert('Пожалуйста, введите название задачи!');
        return;
    }
    
    if (!datetime) {
        alert('Пожалуйста, выберите дату и время!');
        return;
    }
    
    // Валидация даты
    const selectedDate = new Date(datetime);
    const now = new Date();
    
    if (selectedDate <= now) {
        alert('Пожалуйста, выберите будущую дату и время!');
        return;
    }
    
    // Отправить на сервер
    fetch('/tasks/new', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'task-title': title,
            'task-description': description,
            'task-datetime': datetime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Задача добавлена!');
            // Очистить форму
            document.getElementById('add-task-form').reset();
            // Перенаправить на dashboard
            window.location.href = '/dashboard';
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка при добавлении задачи');
    });
    
    alert('✓ Задача успешно добавлена:\n\nНазвание: ' + title + '\nДата: ' + formatDateTime(datetime));

    // Очистить форму
    document.getElementById('add-task-form').reset();
}

// Начать голосовую запись
function startVoiceRecording() {
    // Проверить поддержку Web Speech API
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        alert('Ваш браузер не поддерживает распознавание речи. Используйте Chrome, Edge или Firefox последних версий.');
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    const btn = document.getElementById('voice-task');
    const originalText = btn.value;
    
    btn.value = '🎤 Слушаю... (говорите)';
    btn.disabled = true;
    
    recognition.onstart = function() {
        console.log('Запись началась...');
    };
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        console.log('Распознано:', transcript);
        
        // Вставить распознанный текст в поле задачи
        document.getElementById('task-title').value = transcript;
        
        alert('Распознано: "' + transcript + '"\n\nВы можете отредактировать и добавить задачу.');
    };
    
    recognition.onerror = function(event) {
        console.error('Ошибка распознавания:', event.error);
        alert('Ошибка при распознавании речи: ' + event.error);
    };
    
    recognition.onend = function() {
        btn.value = originalText;
        btn.disabled = false;
    };
    
    try {
        recognition.start();
    } catch (e) {
        console.error('Ошибка при запуске распознавания:', e);
        btn.value = originalText;
        btn.disabled = false;
    }
}

// Функция для форматирования даты и времени
function formatDateTime(dateTimeString) {
    const date = new Date(dateTimeString);
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('ru-RU', options);
}

// Парсинг естественного языка для сроков (примеры)
function parseNaturalDatetime(text) {
    const today = new Date();
    const patterns = {
        'завтра': () => {
            const d = new Date(today);
            d.setDate(d.getDate() + 1);
            return d;
        },
        'на следующей неделе': () => {
            const d = new Date(today);
            d.setDate(d.getDate() + 7);
            return d;
        },
        'через (\\d+) дн': (match) => {
            const days = parseInt(match[1]);
            const d = new Date(today);
            d.setDate(d.getDate() + days);
            return d;
        }
    };
    
    for (let pattern in patterns) {
        if (text.toLowerCase().includes(pattern)) {
            return patterns[pattern]();
        }
    }
    
    return null;
}
