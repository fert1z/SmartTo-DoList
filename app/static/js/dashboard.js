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
    fetch('/api/tasks', { credentials: 'same-origin' })
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

        const inner = document.createElement('div');
        inner.className = 'task-card-inner';
        inner.style.borderTop = '4px solid ' + priorityColor;

        const titleEl = document.createElement('h3');
        titleEl.className = 'task-title';
        titleEl.textContent = task.title || '';
        inner.appendChild(titleEl);

        if (task.description) {
            const descEl = document.createElement('p');
            descEl.className = 'task-description';
            descEl.textContent = task.description;
            inner.appendChild(descEl);
        }

        const metaEl = document.createElement('p');
        metaEl.className = 'task-meta';

        const dateSpan = document.createElement('span');
        dateSpan.className = 'task-date';
        dateSpan.textContent = '🗓️ ' + formatDate(task.due_date);
        metaEl.appendChild(dateSpan);

        const prSpan = document.createElement('span');
        prSpan.className = 'task-priority-badge';
        prSpan.style.background = priorityColor;
        prSpan.textContent = getPriorityLabel(task.priority);
        metaEl.appendChild(prSpan);

        inner.appendChild(metaEl);

        const actionsEl = document.createElement('div');
        actionsEl.className = 'task-actions';

        if (task.status === 'completed') {
            const doneLabel = document.createElement('span');
            doneLabel.className = 'task-done-label';
            doneLabel.textContent = 'Выполнено';
            actionsEl.appendChild(doneLabel);

            const delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'btn-delete';
            delBtn.setAttribute('data-action', 'delete');
            delBtn.setAttribute('data-task-id', String(task.id));
            delBtn.textContent = 'Удалить';
            actionsEl.appendChild(delBtn);
        } else {
            const completeBtn = document.createElement('button');
            completeBtn.type = 'button';
            completeBtn.className = 'btn-complete';
            completeBtn.setAttribute('data-action', 'complete');
            completeBtn.setAttribute('data-task-id', String(task.id));
            completeBtn.textContent = 'Выполнено';
            actionsEl.appendChild(completeBtn);

            const delBtn = document.createElement('button');
            delBtn.type = 'button';
            delBtn.className = 'btn-delete';
            delBtn.setAttribute('data-action', 'delete');
            delBtn.setAttribute('data-task-id', String(task.id));
            delBtn.textContent = 'Удалить';
            actionsEl.appendChild(delBtn);
        }

        inner.appendChild(actionsEl);
        card.appendChild(inner);
        taskBoard.appendChild(card);
    });
}

function completeTask(taskId) {
    fetch('/api/tasks/' + taskId + '/complete', {
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

    fetch('/api/tasks/' + taskId, {
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
