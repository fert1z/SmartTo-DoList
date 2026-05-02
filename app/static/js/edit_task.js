document.addEventListener('DOMContentLoaded', function () {
    const taskId = getTaskIdFromPath();
    const form = document.getElementById('editTaskForm');
    const messageBox = document.getElementById('edit-task-message');

    if (!taskId || !form) {
        return;
    }

    loadTask(taskId);
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        submitTaskUpdate(taskId);
    });
});

function getTaskIdFromPath() {
    const match = window.location.pathname.match(/\/tasks\/(\d+)\/edit$/);
    return match ? parseInt(match[1], 10) : null;
}

function loadTask(taskId) {
    fetch('/tasks/' + taskId, { credentials: 'same-origin' })
        .then(function (response) {
            if (response.status === 401) {
                window.location.href = '/auth/login';
                return null;
            }
            return response.json();
        })
        .then(function (task) {
            if (!task) {
                return;
            }
            const title = document.getElementById('task-title');
            const description = document.getElementById('task-description');
            const priority = document.getElementById('task-priority');
            const category = document.getElementById('task-category');
            const datetime = document.getElementById('task-datetime');

            if (title) title.value = task.title || '';
            if (description) description.value = task.description || '';
            if (priority) priority.value = task.priority || 'medium';
            if (category) category.value = task.category || 'personal';
            if (datetime) datetime.value = formatForDatetimeLocal(task.due_date);
        })
        .catch(function (err) {
            showMessage('Не удалось загрузить задачу.', true);
            console.error(err);
        });
}

function formatForDatetimeLocal(value) {
    if (!value) {
        return '';
    }
    const date = new Date(value);
    if (isNaN(date.getTime())) {
        return '';
    }
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

function submitTaskUpdate(taskId) {
    const title = (document.getElementById('task-title') || {}).value || '';
    const description = (document.getElementById('task-description') || {}).value || '';
    const priority = (document.getElementById('task-priority') || {}).value || 'medium';
    const category = (document.getElementById('task-category') || {}).value || 'personal';
    const datetime = (document.getElementById('task-datetime') || {}).value || '';

    if (!title.trim()) {
        showMessage('Введите название задачи.', true);
        return;
    }

    const payload = {
        title: title.trim(),
        description: description.trim(),
        priority: priority,
        category: category,
        due_date: datetime || '',
    };

    fetch('/tasks/' + taskId, {
        method: 'PUT',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
        },
        body: JSON.stringify(payload),
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
                showMessage('Задача успешно обновлена.', false);
                setTimeout(function () {
                    window.location.href = '/dashboard';
                }, 800);
                return;
            }
            showMessage(data.error || 'Не удалось обновить задачу.', true);
        })
        .catch(function (err) {
            showMessage('Ошибка сети. Попробуйте позже.', true);
            console.error(err);
        });
}

function showMessage(text, isError) {
    const messageBox = document.getElementById('edit-task-message');
    if (!messageBox) {
        alert(text);
        return;
    }
    messageBox.textContent = text;
    messageBox.className = 'addtask-message ' + (isError ? 'addtask-message--error' : 'addtask-message--ok');
    messageBox.hidden = false;
}
