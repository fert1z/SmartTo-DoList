// Dashboard — загрузка задач, фильтр, выполнение и удаление через API

let allTasks = [];
let currentFilter = 'active';
let currentCategory = 'all';
let currentQuery = '';
let currentPage = 1;

document.addEventListener('DOMContentLoaded', function () {
    loadTasks();

    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const q = (document.getElementById('search-input') || {}).value || '';
            currentQuery = q.trim();
            currentPage = 1;
            loadTasks();
        });
    }

    const categorySelect = document.getElementById('category-select');
    if (categorySelect) {
        categorySelect.addEventListener('change', function () {
            currentCategory = categorySelect.value;
            currentPage = 1;
            loadTasks();
        });
    }

    const clearCompletedBtn = document.getElementById('clear-completed');
    if (clearCompletedBtn) {
        clearCompletedBtn.addEventListener('click', function () {
            if (!confirm('Удалить все выполненные задачи?')) return;
            clearCompletedTasks();
        });
    }

    document.querySelectorAll('.filter-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.filter-tab').forEach(function (t) {
                t.classList.remove('filter-tab--active');
            });
            tab.classList.add('filter-tab--active');
            currentFilter = tab.getAttribute('data-filter') || 'active';
            currentPage = 1;
            loadTasks();
        });
    });

    const board = document.getElementById('task-board');
    if (board) {
        board.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const id = parseInt(btn.getAttribute('data-task-id'), 10);
            if (!id) return;
            const action = btn.getAttribute('data-action');
            if (action === 'complete') {
                completeTask(id);
            } else if (action === 'delete') {
                deleteTask(id);
            } else if (action === 'edit') {
                window.location.href = '/tasks/' + id + '/edit';
            }
        });
    }
});

function loadTasks(page = 1) {
    const toast = document.getElementById('dashboard-toast');
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('status', currentFilter);
    params.set('category', currentCategory);
    if (currentQuery) {
        params.set('q', currentQuery);
    }

    fetch('/tasks/list?' + params.toString(), { credentials: 'same-origin' })
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
            allTasks = data.tasks || [];
            currentPage = data.pagination.page || page;
            renderTasks(allTasks);
            renderPager(data.pagination);
        })
        .catch(function (err) {
            console.error(err);
            showToast('Не удалось загрузить задачи. Проверьте соединение.', 'error');
        });
}

function renderPager(pagination) {
    const pager = document.getElementById('task-pager');
    if (!pager) return;
    pager.innerHTML = '';
    if (!pagination || pagination.pages <= 1) {
        return;
    }
    const prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'pager-btn';
    prevBtn.textContent = '◀ Назад';
    prevBtn.disabled = pagination.page <= 1;
    prevBtn.addEventListener('click', function () {
        loadTasks(pagination.page - 1);
    });

    const nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'pager-btn';
    nextBtn.textContent = 'Вперед ▶';
    nextBtn.disabled = pagination.page >= pagination.pages;
    nextBtn.addEventListener('click', function () {
        loadTasks(pagination.page + 1);
    });

    const label = document.createElement('span');
    label.className = 'pager-label';
    label.textContent = 'Стр. ' + pagination.page + ' / ' + pagination.pages;

    pager.appendChild(prevBtn);
    pager.appendChild(label);
    pager.appendChild(nextBtn);
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
        const urgencyLabel = getUrgencyLabel(task);
        const actions =
            task.status === 'completed'
                ? '<div class="task-actions"><span class="task-done-label">Выполнено</span>' +
                  '<button type="button" class="btn-edit" data-action="edit" data-task-id="' +
                  task.id +
                  '">Редактировать</button>' +
                  '<button type="button" class="btn-delete" data-action="delete" data-task-id="' +
                  task.id +
                  '">Удалить</button></div>'
                : '<div class="task-actions">' +
                  '<button type="button" class="btn-edit" data-action="edit" data-task-id="' +
                  task.id +
                  '">Редактировать</button>' +
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
            '<span class="task-category">' +
            escapeHtml(task.category || 'Без категории') +
            '</span>' +
            (urgencyLabel ? '<span class="task-urgency-label">' + urgencyLabel + '</span>' : '') +
            '</p>' +
            actions +
            '</div>';

        taskBoard.appendChild(card);
    });
}

function completeTask(taskId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    fetch('/tasks/' + taskId + '/complete', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
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
            loadTasks(currentPage);
        })
        .catch(function () {
            showToast('Ошибка сети', 'error');
        });
}

function deleteTask(taskId) {
    if (!confirm('Удалить эту задачу?')) return;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    fetch('/tasks/' + taskId, {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {
            Accept: 'application/json',
            'X-CSRFToken': csrfToken,
        },
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
            loadTasks(currentPage);
        })
        .catch(function () {
            showToast('Ошибка сети', 'error');
        });
}

function clearCompletedTasks() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    fetch('/tasks/clear-completed', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
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
            showToast('Выполненные задачи очищены', 'success');
            loadTasks(1);
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

function getUrgencyLabel(task) {
    if (task.status === 'completed') {
        return '';
    }
    if (task.urgency === 'overdue') {
        return '⛔ Просрочено';
    }
    if (task.urgency === 'imminent') {
        return '⚠️ Срочно';
    }
    if (task.urgency === 'soon') {
        return '🔔 Скоро';
    }
    return '';
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
