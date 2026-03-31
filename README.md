# SmartTo-DoList

Умное приложение для управления задачами и напоминаниями с поддержкой искусственного интеллекта.

## 🌟 Основные функции

- ✅ **Управление задачами** - создавайте, редактируйте и удаляйте задачи
- 🧠 **Умные напоминания** - система автоматически определяет приоритет и оптимальное время
- 📱 **Интеграция с Telegram** - получайте уведомления прямо в мессенджер
- 🗣️ **Распознавание речи** - добавляйте задачи голосом
- ⏰ **Гибкие сроки** - используйте естественный язык для указания сроков
- 📊 **Статистика** - отслеживайте вашу продуктивность
- 🔐 **Безопасная аутентификация** - защитите ваши данные

## 📋 Требования

- Python 3.8+
- Flask 2.0+
- SQLAlchemy 1.4+
- SQLite или PostgreSQL

## 🚀 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/yourusername/SmartTo-DoList.git
cd SmartTo-DoList
```

### 2. Создание виртуального окружения
```bash
python -m venv venv

# На Windows:
venv\Scripts\activate

# На Linux/Mac:
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Установка переменных окружения
```bash
# Создайте файл .env в корне проекта:
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 5. Инициализация базы данных
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 6. Запуск приложения
```bash
# Для разработки:
python wsgi.py

# Или с использованием Flask:
flask run

# Для продакшена (с Gunicorn):
gunicorn wsgi:app
```

Приложение будет доступно по адресу: **http://localhost:5000**

## 📁 Структура проекта

```
SmartTo-DoList/
├── app/                        # Основное приложение Flask
│   ├── __init__.py            # Инициализация и create_app()
│   ├── models/                # Модели базы данных
│   ├── routes/                # Маршруты приложения (blueprints)
│   ├── static/                # Статические файлы
│   │   ├── css/              # Стили
│   │   └── js/               # JavaScript
│   └── templates/             # HTML шаблоны
├── instance/                  # Файлы экземпляра приложения
│   └── users.db              # База данных SQLite
├── tg_bot/                   # Telegram бот
├── tests/                    # Unit-тесты
├── config.py                 # Конфигурация приложения
├── wsgi.py                   # Entry point для продакшена
├── requirements.txt          # Зависимости Python
├── .env.example             # Пример переменных окружения
├── .gitignore              # Git ignore файл
└── README.md               # Этот файл
```

## 🔐 Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-super-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost/smarttodolist

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_API_URL=https://api.telegram.org

# Mail (опционально)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## 💻 Разработка

### Запуск тестов
```bash
pytest tests/
```

### Проверка кода (Linting)
```bash
flake8 app/
pylint app/
```

### Форматирование кода
```bash
black app/
```

## 📊 Использование API

### Основные эндпоинты

- `GET /` - главная страница
- `GET /about` - информация о проекте
- `GET /login` - страница входа
- `POST /login` - вход в систему
- `GET /register` - страница регистрации
- `POST /register` - создание аккаунта
- `GET /dashboard` - панель управления
- `POST /api/tasks` - создание задачи
- `GET /api/tasks` - получение списка задач
- `PUT /api/tasks/<id>` - обновление задачи
- `DELETE /api/tasks/<id>` - удаление задачи

## 🤝 Вклад в проект

Мы приветствуем вклад! Пожалуйста:

1. Fork репозиторий
2. Создайте ветку для функции (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push на ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Проект распространяется под лицензией MIT. Подробнее см. [LICENSE](LICENSE).

## 👥 Автор

**SmartTo-DoList Development Team**

- GitHub: [@smarttolist](https://github.com/smarttolist)
- Telegram: [@smarttodolist](https://t.me/smarttodolist)
- Email: support@smarttodolist.com

## 🙏 Благодарности

Спасибо всем, кто помогает развивать этот проект!

## ❓ Поддержка

Если у вас есть вопросы или предложения:
- Откройте [Issue](https://github.com/smarttolist/SmartTo-DoList/issues)
- Свяжитесь через [Email](mailto:support@smarttodolist.com)
- Присоединяйтесь к нашему [Telegram каналу](https://t.me/smarttodolist)

---

**© 2026 SmartTo-DoList. Все права защищены.**
