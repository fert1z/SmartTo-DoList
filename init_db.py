import os
from dotenv import load_dotenv

# Находим путь к файлу .env в корне проекта и принудительно загружаем его
base_dir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(base_dir, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Твой старый код, который идет дальше:
from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    print("База данных успешно инициализирована!")