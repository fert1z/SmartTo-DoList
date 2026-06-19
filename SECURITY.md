# 🔐 SmartTo-DoList Security

## Recent Security Enhancements

### 🔒 Password Hashing
- All passwords are now hashed using `werkzeug.security.generate_password_hash`
- Uses the PBKDF2 algorithm with a salt by default

### 🛡️ CSRF Protection
- Flask-WTF CSRF protection is enabled
- All forms must include a CSRF token
- Configured at the application level

### 📧 Input Validation
- **Username**: Only letters, numbers, and underscores (3-20 characters)
- **Password**: Minimum 8 characters, maximum 128 characters

### 🔑 Telegram Tokens
- Token length increased from 8 to 16 characters (2^64 combinations)
- Format: 16 characters A-F0-9 (hexadecimal)
- TTL: 15 minutes

### 🎯 Authentication
- `@require_login` decorator to protect routes
- Session marked as permanent (`session.permanent = True`)
- `user_id` checked on every request to protected routes

### 📝 Exception Handling
- Try-except blocks in all critical operations
- Transaction rollback (`db.session.rollback()`) on errors
- Logging of all errors

### 📊 Logging
- File-based logging with rotation (10 MB)
- Separate logs for errors (`error.log`)
- Logging of all authentication and critical events

## 🔧 How to Use

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Environment
```bash
# Copy and edit .env.example
cp .env.example .env

# Set a strong SECRET_KEY
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### Run Tests
```bash
pytest tests/
pytest tests/ --cov=app --cov-report=html
```

## 🚨 Production Recommendations

1. **SECRET_KEY**: Use a strong, random key
```python
import secrets
SECRET_KEY = secrets.token_hex(32)
```

2. **HTTPS**: Always use HTTPS in production
```python
SESSION_COOKIE_SECURE = True  # Send cookies only over HTTPS
```

3. **Database**: Use PostgreSQL instead of SQLite
```
DATABASE_URL=postgresql://user:password@localhost/smarttodo
```

4. **TELEGRAM_BOT_TOKEN**: Do not commit tokens, use .env

5. **Logging**: Regularly check logs for security errors

## 📋 Deployment Checklist

- [ ] Strong `SECRET_KEY` is set
- [ ] HTTPS is enabled
- [ ] `DEBUG = False`
- [ ] Using a production-level database (like PostgreSQL)
- [ ] Database backups are configured
- [ ] Logging is enabled
- [ ] Tests are passing (`pytest tests/`)
- [ ] Dependency security checked (`pip audit`)

## 🐛 Reporting Vulnerabilities

If you discover a vulnerability:
1. **Do not create a public Issue**
2. Contact the team via email
3. Describe the vulnerability and steps to reproduce

## 📚 References

- [OWASP Top 10](https://owasp.org/Top10/)
- [Flask Security](https://flask.palletsprojects.com/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/orm/persistence_techniques.html)
- 
