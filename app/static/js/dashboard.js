// Dashboard JavaScript - Функции управления задачами

// Загрузка задач при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadTasks();
    
    // Поиск задач
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchQuery = document.getElementById('search-input').value;
            filterTasks(searchQuery);
        });
    }
});

// Загрузить все задачи
function loadTasks() {
    fetch('/tasks/list')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Ошибка: ' + data.error);
                return;
            }
            renderTasks(data.tasks || []);
        })
        .catch(error => {
            console.error('Ошибка загрузки задач:', error);
            // Fallback to example data
            const tasks = [
                {
                    id: 1,
                    title: 'Купить продукты',
                    description: 'Молоко, хлеб, яйца',
                    due_date: '2026-04-01',
                    priority: 'high'
                },
                {
                    id: 2,
                    title: 'Подготовить презентацию',
                    description: 'Проект по смартным напоминаниям',
                    due_date: '2026-04-05',
                    priority: 'medium'
                },
                {
                    id: 3,
                    title: 'Позвонить маме',
                    description: 'Проверить как дела',
                    due_date: '2026-04-02',
                    priority: 'low'
                }
            ];
            renderTasks(tasks);
        });
}

// Отрисовать задачи на странице
function renderTasks(tasks) {
    const taskBoard = document.getElementById('task-board');
    if (!taskBoard) return;
    
    taskBoard.innerHTML = '';
    
    if (tasks.length === 0) {
        taskBoard.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #666;">Нет задач</p>';
        return;
    }
    
    tasks.forEach(task => {
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        
        const priorityColor = getPriorityColor(task.priority);
        
        taskCard.innerHTML = `
            <div style="border-bottom: 3px solid ${priorityColor}; padding-bottom: 10px;">
                <h3 class="task-title">${escapeHtml(task.title)}</h3>
                <p class="task-description">${escapeHtml(task.description || '')}</p>
                <p class="task-date">🗓️ ${formatDate(task.due_date)}</p>
                <span style="display: inline-block; background-color: ${priorityColor}; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px;">
                    ${getPriorityLabel(task.priority)}
                </span>
            </div>
            <div class="task-actions">
                <button class="btn-complete" onclick="completeTask(${task.id})">✓ Выполнено</button>
                <button class="btn-delete" onclick="deleteTask(${task.id})">✕ Удалить</button>
            </div>
        `;
        
        taskBoard.appendChild(taskCard);
    });
}

// Фильтрация задач по поиску
function filterTasks(query) {
    // В реальном приложении здесь будет запрос к серверу
    console.log('Поиск по: ' + query);
    alert('Поиск: ' + query);
}

// Отметить задачу как выполненную
function completeTask(taskId) {
    alert('Задача #' + taskId + ' отмечена как выполненная!');
    // В реальном приложении: отправить на сервер и обновить список
}

// Удалить задачу
function deleteTask(taskId) {
    if (confirm('Вы уверены, что хотите удалить эту задачу?')) {
        alert('Задача #' + taskId + ' удалена!');
        // В реальном приложении: отправить на сервер и обновить список
    }
}

// Вспомогательные функции
function getPriorityColor(priority) {
    switch(priority) {
        case 'high': return '#dc3545';
        case 'medium': return '#ffc107';
        case 'low': return '#28a745';
        default: return '#6c757d';
    }
}

function getPriorityLabel(priority) {
    switch(priority) {
        case 'high': return 'Высокий приоритет';
        case 'medium': return 'Средний приоритет';
        case 'low': return 'Низкий приоритет';
        default: return 'Неизвестно';
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('ru-RU', options);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
