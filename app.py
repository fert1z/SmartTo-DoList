"""
SmartTo-DoList - главный файл приложения
Для разработки используйте: python app.py
Для продакшена используйте: wsgi.py с Gunicorn
"""
from wsgi import app

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False), port=5000)
