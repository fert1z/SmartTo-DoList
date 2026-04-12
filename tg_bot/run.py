"""
Запуск бота: из корня проекта
  python -m tg_bot.run
Переменная TELEGRAM_BOT_TOKEN обязательна (файл .env подхватывается, если установлен python-dotenv).
"""
from tg_bot.main_bot import run_polling

if __name__ == '__main__':
    run_polling()
