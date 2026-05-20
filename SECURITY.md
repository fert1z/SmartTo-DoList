# 🔐 Безопасность SmartTo-DoList

## Последние улучшения безопасности

### 🔒 Хеширование паролей
- Все пароли теперь хешируются с использованием `werkzeug.security.generate_password_hash`
- Используется алгоритм PBKDF2 с солью по умолчанию

### 🛡️ CSRF защита
- Включена Flask-WTF CSRF защита
- Все формы должны содержать CSRF токен
- Настроено на уровне приложения

### 📧 Валидация входных данных
- **Email**: Валидация формата с помощью `email-validator`
- **Username**: Только буквы, цифры, подчеркивание (3-20 символов)
- **Пароль**: Минимум 8 символов, максимум 128 символов

### 🔑 Токены Telegram
- Увеличена длина токена с 8 до 16 символов (2^64 комбинаций)
- Формат: 16 символов A-F0-9 (шестнадцатеричная система)
- TTL: 15 минут

### 🎯 Аутентификация
- Декоратор `@require_login` для защиты маршрутов
- Сессия помечена как постоянная (`session.permanent = True`)
- Проверка user_id при каждом запросе к защищенным маршрутам

### 📝 Обработка исключений
- Try-except блоки во всех критических операциях
- Откат транзакций (`db.session.rollback()`) при ошибках
- Логирование всех ошибок

### 📊 Логирование
- Файловое логирование с ротацией (10 MB)
- Отдельные логи для ошибок (`error.log`)
- Логирование всех операций аутентификации и критических событий

## 🔧 Как использовать

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Конфигурация окружения
```bash
# Скопируйте и отредактируйте .env.example
cp .env.example .env

# Установите сильный SECRET_KEY
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### Запуск тестов
```bash
pytest tests/
pytest tests/ --cov=app --cov-report=html
```

## 🚨 Рекомендации для продакшена

1. **SECRET_KEY**: Используйте сильный случайный ключ
```python
import secrets
SECRET_KEY = secrets.token_hex(32)
```

2. **HTTPS**: Всегда используйте HTTPS в продакшене
```python
SESSION_COOKIE_SECURE = True  # Отправлять куки только по HTTPS
```

3. **Database**: Используйте PostgreSQL вместо SQLite
```
DATABASE_URL=postgresql://user:password@localhost/smarttodo
```

4. **TELEGRAM_BOT_TOKEN**: Не коммитьте токены, используйте .env

5. **Логирование**: Регулярно проверяйте логи на ошибки безопасности

## 📋 Чек-лист для развертывания

- [ ] Установлен сильный `SECRET_KEY`
- [ ] Включен HTTPS
- [ ] `DEBUG = False`
- [ ] Используется PostgreSQL (или другая БД уровня production)
- [ ] Настроены резервные копии БД
- [ ] Включено логирование
- [ ] Запущены тесты (`pytest tests/`)
- [ ] Проверена безопасность зависимостей (`pip audit`)

## 🐛 报告об уязвимостях

Если вы обнаружили уязвимость:
1. **Не создавайте публичный Issue**
2. Свяжитесь с командой через почту
3. Опишите уязвимость и шаги для воспроизведения

## 📚 Ссылки

- [OWASP Top 10](https://owasp.org/Top10/)
- [Flask Security](https://flask.palletsprojects.com/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/orm/persistence_techniques.html)
