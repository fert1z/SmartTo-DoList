"""
SmartTo-DoList - главный файл приложения
Для разработки используйте: python app.py
Для продакшена используйте: wsgi.py с Gunicorn
"""
from wsgi import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
