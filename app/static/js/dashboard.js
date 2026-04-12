// Dashboard — загрузка задач, фильтр, выполнение и удаление через API

let allTasks = [];
let currentFilter = 'active';

document.addEventListener('DOMContentLoaded', function () {
    loadTasks();

    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const q = (document.getElementById('search-input') || {}).value || '';
            applyFilterAndSearch(q.trim().toLowerCase());
        });
    }

    document.querySelectorAll('.filter-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.filter-tab').forEach(function (t) {
                t.classList.remove('filter-tab--active');
            });
            tab.classList.add('filter-tab--active');
            currentFilter = tab.getAttribute('data-filter') || 'active';
            const q = (document.getElementById('search-input') || {}).value || '';
            applyFilterAndSearch(q.trim().toLowerCase());
        });
    });

    const board = document.getElementById('task-board');
    if (board) {
        board.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const id = parseInt(btn.getAttribute('data-task-id'), 10);
            if (!id) return;
            if (btn.getAttribute('data-action') === 'complete') {
                completeTask(id);
            } else if (btn.getAttribute('data-action') === 'delete') {
                deleteTask(id);
            }
        });
    }
});

function loadTasks() {
    const toast = document.getElementById('dashboard-toast');
    fetch('/tasks/list', { credentials: 'same-origin' })
        .then(function (response) {
            if (response.status === 401) {
                window.location.href = '/auth/login';
                return null;
            }
            return response.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            allTasks = Array.isArray(data) ? data : data.tasks || [];
            const q = (document.getElementById('search-input') || {}).value || '';
            applyFilterAndSearch(q.trim().toLowerCase());
        })
        .catch(function (err) {
            console.error(err);
            showToast('Не удалось загрузить задачи. Проверьте соединение.', 'error');
        });
}

function applyFilterAndSearch(queryLower) {
    let list = allTasks.slice();
    if (currentFilter === 'active') {
        list = list.filter(function (t) {
            return t.status !== 'completed';
        });
    } else if (currentFilter === 'done') {
        list = list.filter(function (t) {
            return t.status === 'completed';
        });
    }
    if (queryLower) {
        list = list.filter(function (t) {
            const title = (t.title || '').toLowerCase();
            const desc = (t.description || '').toLowerCase();
            return title.indexOf(queryLower) !== -1 || desc.indexOf(queryLower) !== -1;
        });
    }
    renderTasks(list);
}

function showToast(message, type) {
    const el = document.getElementById('dashboard-toast');
    if (!el) {
        if (type === 'error') alert(message);
        return;
    }
    el.textContent = message;
    el.className = 'dashboard-toast dashboard-toast--' + (type || 'info');
    el.hidden = false;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(function () {
        el.hidden = true;
    }, 4000);
}

function renderTasks(tasks) {
    const taskBoard = document.getElementById('task-board');
    if (!taskBoard) return;

    taskBoard.innerHTML = '';

    if (tasks.length === 0) {
        taskBoard.innerHTML =
            '<p class="task-board-empty">Нет задач по выбранному фильтру. ' +
            '<a href="/addtask">Создать задачу</a></p>';
        return;
    }

    tasks.forEach(function (task) {
        const card = document.createElement('article');
        card.className = 'task-card';
        if (task.status === 'completed') {
            card.classList.add('task-card--completed');
        }

        const priorityColor = getPriorityColor(task.priority);
        const actions =
            task.status === 'completed'
                ? '<div class="task-actions"><span class="task-done-label">Выполнено</span>' +
                  '<button type="button" class="btn-delete" data-action="delete" data-task-id="' +
                  task.id +
                  '">Удалить</button></div>'
                : '<div class="task-actions">' +
                  '<button type="button" class="btn-complete" data-action="complete" data-task-id="' +
                  task.id +
                  '">Выполнено</button>' +
                  '<button type="button" class="btn-delete" data-action="delete" data-task-id="' +
                  task.id +
                  '">Удалить</button></div>';

        card.innerHTML =
            '<div class="task-card-inner" style="border-top: 4px solid ' +
            priorityColor +
            '">' +
            '<h3 class="task-title">' +
            escapeHtml(task.title) +
            '</h3>' +
            (task.description
                ? '<p class="task-description">' + escapeHtml(task.description) + '</p>'
                : '') +
            '<p class="task-meta">' +
            '<span class="task-date">🗓️ ' +
            formatDate(task.due_date) +
            '</span>' +
            '<span class="task-priority-badge" style="background:' +
            priorityColor +
            '">' +
            getPriorityLabel(task.priority) +
            '</span>' +
            '</p>' +
            actions +
            '</div>';

        taskBoard.appendChild(card);
    });
}

function completeTask(taskId) {
    fetch('/tasks/' + taskId + '/complete', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
    })
        .then(function (r) {
            if (r.status === 401) {
                window.location.href = '/auth/login';
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            showToast('Задача отмечена выполненной', 'success');
            loadTasks();
        })
        .catch(function () {
            showToast('Ошибка сети', 'error');
        });
}

function deleteTask(taskId) {
    if (!confirm('Удалить эту задачу?')) return;

    fetch('/tasks/' + taskId, {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
    })
        .then(function (r) {
            if (r.status === 401) {
                window.location.href = '/auth/login';
                return null;
            }
            return r.json();
        })
        .then(function (data) {
            if (!data) return;
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            showToast('Задача удалена', 'success');
            loadTasks();
        })
        .catch(function () {
            showToast('Ошибка сети', 'error');
        });
}

function getPriorityColor(priority) {
    switch (priority) {
        case 'high':
            return '#e53935';
        case 'medium':
            return '#fb8c00';
        case 'low':
            return '#43a047';
        default:
            return '#78909c';
    }
}

function getPriorityLabel(priority) {
    switch (priority) {
        case 'high':
            return 'Высокий';
        case 'medium':
            return 'Средний';
        case 'low':
            return 'Низкий';
        default:
            return '—';
    }
}

function formatDate(dateString) {
    if (!dateString) return 'Без срока';
    var d = new Date(dateString);
    if (isNaN(d.getTime())) return 'Без срока';
    return d.toLocaleString('ru-RU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text == null ? '' : text;
    return div.innerHTML;
}
