"""Утилиты для валидации и аутентификации"""
import re
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta, timezone
import pytz
import logging

logger = logging.getLogger(__name__)

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
    Реализует все правила расчетов: интервалы, абстрактные дни, дни недели, размытое время.
    Возвращает datetime в UTC.
    """
    logger.info("--- RUNNING NEW ADVANCED LOCAL PARSER ---")
    if not text:
        return None
        
    text = text.lower().strip()
    # Очистка мусорных слов
    text = re.sub(r'\b(напомни|сделать|записать|в районе|под|на|в|до)\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc

    now = datetime.now(tz)
    
    target_date = now.date()
    target_time = None
    
    # 1. Относительные смещения (Интервалы)
    if 'через' in text or 'назад' in text:
        is_past = 'назад' in text
        multiplier = -1 if is_past else 1
        total_minutes = 0
        days_add = 0
        
        if 'полчаса' in text:
            total_minutes += 30
        elif 'полтора часа' in text:
            total_minutes += 90
        elif 'четверть часа' in text:
            total_minutes += 15
        elif 'час' in text:
            total_minutes += 60

            
        min_match = re.search(r'(\d+)\s*мин', text)
        if min_match: total_minutes += int(min_match.group(1))
            
        hour_match = re.search(r'(\d+)\s*час', text)
        if hour_match: total_minutes += int(hour_match.group(1)) * 60
            
        day_match = re.search(r'(\d+)\s*д(ень|ня|ней)', text)
        if day_match: days_add += int(day_match.group(1))
            
        week_match = re.search(r'(\d+)\s*недел', text)
        if week_match: days_add += int(week_match.group(1)) * 7
            
        month_match = re.search(r'(\d+)\s*месяц', text)
        if month_match: days_add += int(month_match.group(1)) * 30 # Упрощенно

        if total_minutes > 0 or days_add > 0:
            target_dt = now + timedelta(days=days_add * multiplier, minutes=total_minutes * multiplier)
            return target_dt.astimezone(pytz.utc)

    # 2. Абстрактные дни
    if 'послезавтра' in text or 'через день' in text:
        target_date = now.date() + timedelta(days=2)
    elif 'завтра' in text:
        target_date = now.date() + timedelta(days=1)
    elif 'сегодня' in text:
        target_date = now.date()
    elif 'позавчера' in text:
        target_date = now.date() - timedelta(days=2)
    elif 'вчера' in text:
        target_date = now.date() - timedelta(days=1)
    
    # 5. Точные даты
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
        if month < now.month or (month == now.month and day < now.day):
            target_year += 1
        try:
            target_date = datetime(target_year, month, day).date()
        except ValueError:
            pass
            
    # 3. Дни недели и недели
    weekdays = {
        'понедельник': 0, 'понедельника': 0, 
        'вторник': 1, 'вторника': 1, 
        'сред': 2, 
        'четверг': 3, 'четверга': 3,
        'пятниц': 4, 
        'суббот': 5, 
        'воскресень': 6
    }
    
    is_next_week_explicit = 'следующ' in text
    
    if 'выходны' in text:
        if now.weekday() < 5:
            days_ahead = 5 - now.weekday()
            target_date = now.date() + timedelta(days=days_ahead)
        else:
            target_date = now.date()
    elif is_next_week_explicit and 'недел' in text and not any(wd in text for wd in weekdays):
        days_ahead = 7 - now.weekday()
        target_date = now.date() + timedelta(days=days_ahead)
    else:
        for wd_name, wd_idx in weekdays.items():
            if wd_name in text:
                days_ahead = wd_idx - now.weekday()
                if is_next_week_explicit:
                    days_ahead += 7
                elif days_ahead <= 0:
                    days_ahead += 7
                
                target_date = now.date() + timedelta(days=days_ahead)
                break

    # 4. Размытое время
    time_words = {
        'утр': 9,
        'обед': 13,
        'днем': 14, 'днём': 14,
        'после работы': 18,
        'вечер': 18,
        'конце дня': 18,
        'ночь': 23
    }
    
    for word, h in time_words.items():
        if word in text:
            target_time = datetime.min.time().replace(hour=h)
            break

    # Точное время (HH:MM или просто часы)
    time_match_exact = re.search(r'(\d{1,2})[.:](\d{2})', text)
    if time_match_exact:
        target_time = datetime.min.time().replace(hour=int(time_match_exact.group(1)), minute=int(time_match_exact.group(2)))
    else:
        hour_only_match = re.search(r'\b(\d{1,2})\b', text)
        if hour_only_match and not exact_date_match:
            h = int(hour_only_match.group(1))
            if h < 8 and 'ноч' not in text: h += 12
            if h <= 23:
                target_time = datetime.min.time().replace(hour=h)

    # Дефолтное время 09:00:00
    if target_time is None and (target_date != now.date() or 'завтра' in text or 'сегодня' in text):
        target_time = datetime.min.time().replace(hour=9)
        
    # Корректировка, если день "сегодня", а время уже прошло
    if target_date == now.date() and target_time and target_time <= now.time() and 'сегодня' not in text:
        target_date += timedelta(days=1)
            
    if target_date == now.date() and target_time is None:
        return None

    if target_time is None:
        target_time = now.time()

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
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return str(dt)