# 👨‍💻 Руководство разработки SmartTo-DoList

## Установка окружения

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd SmartTo-DoList
```

### 2. Создание виртуального окружения
```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Конфигурация окружения
```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env
nano .env
```

### 5. Инициализация БД
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

## Запуск приложения

### Development режим
```bash
python wsgi.py
# Или
python app.py
```

Приложение будет доступно на `http://localhost:5000`

### Telegram бот
```bash
python -m tg_bot.run
```

## Тестирование

### Запуск всех тестов
```bash
pytest tests/ -v
```

### Запуск с покрытием
```bash
pytest tests/ --cov=app --cov-report=html
```

### Запуск конкретного теста
```bash
pytest tests/test_app.py::TestAuth::test_login_valid -v
```

## Разработка

### Структура проекта
```
SmartTo-DoList/
├── app/
│   ├── __init__.py           # Инициализация приложения
│   ├── models.py             # Модели БД
│   ├── utils.py              # Утилиты и валидация
│   ├── logging_config.py     # Конфигурация логирования
│   ├── routes/               # Маршруты (blueprints)
│   │   ├── auth.py          # Аутентификация
│   │   ├── tasks.py         # Управление задачами
│   │   ├── account.py       # Профиль и аккаунт
│   │   └── main.py          # Основные маршруты
│   ├── static/               # Статические файлы (CSS, JS)
│   └── templates/            # HTML шаблоны
├── tg_bot/                   # Telegram бот
├── tests/                    # Тесты
├── config.py                 # Конфигурация
├── wsgi.py                   # WSGI entry point
└── requirements.txt          # Зависимости
```

### Добавление нового маршрута

1. Создайте функцию в соответствующем файле в `app/routes/`
2. Используйте декоратор `@require_login` для защиты
3. Добавьте обработку исключений
4. Логируйте важные события

```python
from flask import Blueprint, render_template, jsonify
from app.utils import require_login
import logging

logger = logging.getLogger(__name__)
my_bp = Blueprint('my_blueprint', __name__)

@my_bp.route('/my-route', methods=['GET', 'POST'])
@require_login
def my_function():
    """Описание функции"""
    try:
        # Ваш код
        logger.info("Action completed successfully")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': 'Произошла ошибка'}), 500
```

### Добавление тестов

1. Создайте класс теста в `tests/test_app.py`
2. Используйте фикстуры `client`, `app`, `auth_user`
3. Названия функций должны начинаться с `test_`

```python
def test_my_feature(self, client, auth_user):
    """Описание теста"""
    with client.session_transaction() as sess:
        sess['user_id'] = auth_user.id
    
    response = client.get('/my-route')
    assert response.status_code == 200
```

### Валидация данных

Используйте функции из `app/utils.py`:

```python
from app.utils import validate_email_format, validate_username, validate_password

# Email
if not validate_email_format(email):
    return jsonify({'error': 'Некорректный email'}), 400

# Username
valid, msg = validate_username(username)
if not valid:
    return jsonify({'error': msg}), 400

# Password
valid, msg = validate_password(password)
if not valid:
    return jsonify({'error': msg}), 400
```

## Best Practices

### 1. Безопасность
- Всегда используйте `@require_login` для защиты маршрутов
- Валидируйте все входные данные
- Используйте параметризованные запросы (ORM)
- Логируйте все подозрительные действия

### 2. Обработка ошибок
```python
try:
    # Ваш код
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"Error: {str(e)}")
    return jsonify({'error': 'Произошла ошибка'}), 500
```

### 3. Логирование
```python
logger.info("User login successful")
logger.warning("Suspicious activity detected")
logger.error("Database connection failed")
```

### 4. Тестирование
- Пишите тесты для новых функций
- Покрытие должно быть > 80%
- Тесты должны быть независимыми

## Команды для разработки

### Форматирование кода
```bash
# Используйте black (если установлен)
black app/
```

### Проверка типов
```bash
# Используйте mypy (если установлен)
mypy app/
```

### Проверка безопасности
```bash
# Проверка зависимостей
pip audit
```

### Генерация документации
```bash
# Если используете Sphinx
sphinx-build -b html docs docs/_build
```

## Отладка

### Flask shell
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     # Ваш код
```

### Логи
```bash
# Просмотр логов
tail -f instance/logs/app.log
tail -f instance/logs/error.log
```

### Отладка в коде
```python
import pdb
pdb.set_trace()  # Breakpoint

# Или используйте логирование
logger.debug(f"Variable value: {variable}")
```

## Рекомендуемые инструменты

- **IDE**: VS Code, PyCharm
- **Линтер**: flake8, pylint
- **Форматер**: black
- **Проверка типов**: mypy
- **Git hook**: pre-commit

## Полезные ссылки

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)

## Контакт

Если у вас есть вопросы о разработке, свяжитесь с командой проекта.
