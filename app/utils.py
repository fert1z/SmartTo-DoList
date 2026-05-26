"""Утилиты для валидации и аутентификации"""
import re
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta, timezone
import pytz

def validate_email_format(email):
    """Валидирует формат email"""
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_username(username):
    """Валидирует username - от 3 до 20 символов, буквы, цифры, подчеркивание"""
    if not username:
        return False, "Username обязателен"
    if len(username) < 3:
        return False, "Username должен быть не менее 3 символов"
    if len(username) > 20:
        return False, "Username не должен превышать 20 символов"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username может содержать только буквы, цифры и подчеркивание"
    return True, None


def validate_password(password):
    """Валидирует пароль"""
    if not password:
        return False, "Пароль обязателен"
    if len(password) < 8:
        return False, "Пароль должен содержать не менее 8 символов"
    if len(password) > 128:
        return False, "Пароль не должен превышать 128 символов"
    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'\d', password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    if not re.search(r'[!@#$%^&*()_+\-=[\]{};:\"\\|,<.>/?]', password):
        return False, "Пароль должен содержать хотя бы один специальный символ"
    return True, None


def parse_natural_time_local(text: str, user_timezone: str = 'UTC') -> datetime | None:
    """
    Мощный локальный парсер естественного языка, заменяющий нейросеть.
    Возвращает datetime в UTC.
    """
    if not text:
        return None
        
    text = text.lower().strip()
    # Убираем лишние слова
    text = re.sub(r'\b(напомни|сделать|записать|в районе|под)\b', '', text).strip()
    
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc

    now = datetime.now(tz)
    
    target_date = now.date()
    target_time = None
    
    # 1. Точные даты: "15 января"
    months = {
        'января': 1, 'январь': 1, 'февраля': 2, 'февраль': 2, 'марта': 3, 'март': 3,
        'апреля': 4, 'апрель': 4, 'мая': 5, 'май': 5, 'июня': 6, 'июнь': 6,
        'июля': 7, 'июль': 7, 'августа': 8, 'август': 8, 'сентября': 9, 'сентябрь': 9,
        'октября': 10, 'октябрь': 10, 'ноября': 11, 'ноябрь': 11, 'декабря': 12, 'декабрь': 12
    }
    month_pattern = '|'.join(months.keys())
    exact_date_match = re.search(rf'(\d{{1,2}})\s+({month_pattern})', text)
    if exact_date_match:
        day = int(exact_date_match.group(1))
        month = months[exact_date_match.group(2)]
        target_year = now.year
        # Перенос на следующий год, если дата уже прошла
        if month < now.month or (month == now.month and day < now.day):
            target_year += 1
        try:
            target_date = datetime(target_year, month, day).date()
        except ValueError:
            return None # Некорректная дата (например, 31 февраля)
            
    # 2. Относительные даты (Абстрактные дни)
    elif 'послезавтра' in text or 'через день' in text:
        target_date = now.date() + timedelta(days=2)
    elif 'завтра' in text:
        target_date = now.date() + timedelta(days=1)
    elif 'сегодня' in text:
        target_date = now.date()
    elif 'позавчера' in text:
        target_date = now.date() - timedelta(days=2)
    elif 'вчера' in text:
        target_date = now.date() - timedelta(days=1)
        
    # 3. Дни недели
    weekdays = {
        'понедельник': 0, 'вторник': 1, 'сред': 2, 'четверг': 3, 
        'пятниц': 4, 'суббот': 5, 'воскресень': 6
    }
    
    # "на выходных"
    if 'на выходных' in text or 'в выходные' in text:
        if now.weekday() < 5: # Если будни, ищем субботу
            days_ahead = 5 - now.weekday()
            target_date = now.date() + timedelta(days=days_ahead)
        else:
            target_date = now.date() # Уже выходные
            
    # "в следующий [день]" или "на следующей неделе"
    elif 'следующ' in text:
        if 'недел' in text and not any(wd in text for wd in weekdays):
            # Просто "на следующей неделе" -> следующий понедельник
            days_ahead = 7 - now.weekday()
            target_date = now.date() + timedelta(days=days_ahead)
        else:
            for wd_name, wd_idx in weekdays.items():
                if wd_name in text:
                    # Ищем день на следующей неделе
                    days_ahead = 7 - now.weekday() + wd_idx
                    target_date = now.date() + timedelta(days=days_ahead)
                    break
    # Просто "в [день]"
    else:
        for wd_name, wd_idx in weekdays.items():
            if wd_name in text:
                days_ahead = wd_idx - now.weekday()
                if days_ahead <= 0: # День уже прошел на этой неделе, берем следующую
                    days_ahead += 7
                target_date = now.date() + timedelta(days=days_ahead)
                break

    # 4. Относительное время (Интервалы)
    if 'через' in text:
        total_minutes = 0
        
        # Полутора
        if 'полтора часа' in text:
            total_minutes += 90
        # Полчаса
        elif 'полчаса' in text:
            total_minutes += 30
        # Четверть часа
        elif 'четверть часа' in text:
            total_minutes += 15
            
        # Минуты
        min_match = re.search(r'через\s+(\d+)\s+мин', text)
        if min_match:
            total_minutes += int(min_match.group(1))
            
        # Часы
        hour_match = re.search(r'через\s+(\d+)\s+час', text)
        if hour_match:
            total_minutes += int(hour_match.group(1)) * 60
            
        # Дни, недели, месяцы
        day_match = re.search(r'через\s+(\d+)\s+д(ень|ня|ней)', text)
        week_match = re.search(r'через\s+(\d+)\s+недел', text)
        month_match = re.search(r'через\s+(\d+)\s+месяц', text)
        
        days_add = 0
        if day_match: days_add += int(day_match.group(1))
        if week_match: days_add += int(week_match.group(1)) * 7
        if month_match: days_add += int(month_match.group(1)) * 30 # Примерно
        
        if total_minutes > 0 or days_add > 0:
            target_dt = now + timedelta(days=days_add, minutes=total_minutes)
            return target_dt.astimezone(pytz.utc)
            
    # "час назад"
    if 'час назад' in text:
        return (now - timedelta(hours=1)).astimezone(pytz.utc)

    # 5. Размытое время
    time_words = {
        'утром': 9, 'с утра': 9,
        'в обед': 13, 'после работы': 18,
        'днем': 14, 'днём': 14,
        'вечером': 18, 'под вечер': 18, 'в конце дня': 18, 'до конца дня': 18,
        'ночью': 23
    }
    
    for word, h in time_words.items():
        if word in text:
            target_time = datetime.min.time().replace(hour=h)
            break

    # Точное время (HH:MM)
    time_match = re.search(r'(?:в\s+)?(\d{1,2})[.:](\d{2})', text)
    if time_match:
        target_time = datetime.min.time().replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)))
    
    # "в 10", "в 5" (если не распознано как дата)
    elif not exact_date_match:
        hour_only_match = re.search(r'\bв\s+(\d{1,2})\b', text)
        if hour_only_match:
            h = int(hour_only_match.group(1))
            # Простая логика: если ввели "в 2", скорее всего это 14:00
            if h < 8 and 'ноч' not in text and 'утр' not in text:
                h += 12
            target_time = datetime.min.time().replace(hour=h)

    # Дефолтное время, если указана только дата (как в промпте)
    if target_time is None and target_date != now.date():
        target_time = datetime.min.time().replace(hour=9) # По умолчанию 9 утра
        
    # Если дата не указана (осталась сегодня), но время уже прошло - переносим на завтра
    if target_date == now.date() and target_time:
        if target_time < now.time():
            target_date = target_date + timedelta(days=1)
            
    # Если вообще ничего не распознано
    if target_date == now.date() and target_time is None:
        return None
        
    # Если время так и не было определено, берем текущее
    if target_time is None:
        target_time = now.time()

    # Собираем итоговый datetime
    final_dt = tz.localize(datetime.combine(target_date, target_time))
    
    return final_dt.astimezone(pytz.utc)


def require_login(f):
    """Декоратор для проверки аутентификации и существования пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Не авторизован'}), 401
            return redirect(url_for('auth.login'))
        # Проверка существования пользователя
        from app.models import User
        user = User.query.get(user_id)
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Не авторизован'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def format_datetime_for_user(dt, timezone_str='UTC'):
    """Форматирует datetime для пользователя с учетом временной зоны"""
    if dt is None:
        return ''
    try:
        # Простая реализация (можно расширить с pytz)
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return str(dt)