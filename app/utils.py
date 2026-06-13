"""Utilities for validation and authentication"""
import re
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta, timezone
import pytz
import logging
from typing import Optional

from app import db

logger = logging.getLogger(__name__)

def validate_email_format(email):
    """Validates email format, raises ValueError on failure."""
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email format: {e}")


def validate_username(username):
    """Validates username, raises ValueError on failure."""
    if not username:
        raise ValueError("Username is required")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long")
    if len(username) > 20:
        raise ValueError("Username must not exceed 20 characters")
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValueError("Username can only contain letters, numbers, and underscores")


def validate_password(password):
    """Validates password, raises ValueError on failure."""
    if not password:
        raise ValueError("Password is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*()_+\-=[\]{};:\"\\|,<.>/?]', password):
        raise ValueError("Password must contain at least one special character")

# --- Refactored Natural Language Time Parser ---

def _parse_relative_time(text: str, now: datetime) -> Optional[datetime]:
    if 'через' in text or 'назад' in text:
        is_past = 'назад' in text
        multiplier = -1 if is_past else 1
        total_minutes = 0
        days_add = 0
        
        if 'полчаса' in text: total_minutes += 30
        elif 'полтора часа' in text: total_minutes += 90
        elif 'четверть часа' in text: total_minutes += 15
        
        hour_match = re.search(r'(\d+)\s*час', text)
        if hour_match: total_minutes += int(hour_match.group(1)) * 60
        elif 'час' in text and not hour_match: total_minutes += 60

        min_match = re.search(r'(\d+)\s*мин', text)
        if min_match: total_minutes += int(min_match.group(1))
            
        day_match = re.search(r'(\d+)\s*д(ень|ня|ней)', text)
        if day_match: days_add += int(day_match.group(1))
            
        week_match = re.search(r'(\d+)\s*недел', text)
        if week_match: days_add += int(week_match.group(1)) * 7
            
        month_match = re.search(r'(\d+)\s*месяц', text)
        if month_match: days_add += int(month_match.group(1)) * 30

        if total_minutes > 0 or days_add > 0:
            return now + timedelta(days=days_add * multiplier, minutes=total_minutes * multiplier)
    return None

def _parse_abstract_days(text: str, now: datetime) -> Optional[datetime.date]:
    if 'послезавтра' in text or 'через день' in text: return now.date() + timedelta(days=2)
    if 'завтра' in text: return now.date() + timedelta(days=1)
    if 'сегодня' in text: return now.date()
    if 'позавчера' in text: return now.date() - timedelta(days=2)
    if 'вчера' in text: return now.date() - timedelta(days=1)
    return None

def _parse_exact_date(text: str, now: datetime) -> Optional[datetime.date]:
    months = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
    month_pattern = '|'.join(months.keys())
    match = re.search(rf'(\d{{1,2}})\s+({month_pattern})', text)
    if match:
        day, month_str = int(match.group(1)), match.group(2)
        month = months[month_str]
        year = now.year + 1 if month < now.month or (month == now.month and day < now.day) else now.year
        try:
            return datetime(year, month, day).date()
        except ValueError:
            pass
    return None

def _parse_weekdays(text: str, now: datetime) -> Optional[datetime.date]:
    weekdays = {'понедельник': 0, 'вторник': 1, 'сред': 2, 'четверг': 3, 'пятниц': 4, 'суббот': 5, 'воскресень': 6}
    is_next_week = 'следующ' in text
    
    if 'выходны' in text:
        return now.date() + timedelta(days=5 - now.weekday()) if now.weekday() < 5 else now.date()
    
    if is_next_week and 'недел' in text and not any(wd in text for wd in weekdays):
        return now.date() + timedelta(days=7 - now.weekday())

    for wd, wd_idx in weekdays.items():
        if wd in text:
            days_ahead = wd_idx - now.weekday()
            if is_next_week or days_ahead <= 0:
                days_ahead += 7
            return now.date() + timedelta(days=days_ahead)
    return None

def _parse_time(text: str) -> Optional[datetime.time]:
    time_words = {'утр': 9, 'обед': 13, 'днем': 14, 'после работы': 18, 'вечер': 18, 'ночь': 23}
    for word, hour in time_words.items():
        if word in text:
            return datetime.min.time().replace(hour=hour)

    match = re.search(r'(\d{1,2})[.:](\d{2})', text)
    if match:
        return datetime.min.time().replace(hour=int(match.group(1)), minute=int(match.group(2)))
    
    match = re.search(r'\b(\d{1,2})\b', text)
    if match and not re.search(r'\d{1,2}\s+(января|февраля|...|декабря)', text): # Avoid matching day of month
        hour = int(match.group(1))
        if hour < 8 and 'ноч' not in text: hour += 12
        if hour <= 23:
            return datetime.min.time().replace(hour=hour)
    return None

def parse_natural_time_local(text: str, user_timezone: str = 'UTC') -> Optional[datetime]:
    logger.info("--- RUNNING REFACTORED LOCAL PARSER ---")
    if not text: return None
        
    text = re.sub(r'\b(напомни|сделать|записать|в районе|под|на|в|до)\b', ' ', text.lower()).strip()
    
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc

    now = datetime.now(tz)
    
    # Relative time has highest priority
    if (result_dt := _parse_relative_time(text, now)):
        return result_dt.astimezone(pytz.utc)

    target_date = _parse_abstract_days(text, now) or \
                  _parse_exact_date(text, now) or \
                  _parse_weekdays(text, now) or \
                  now.date()

    target_time = _parse_time(text)

    # Default time logic
    if target_time is None and target_date != now.date():
        target_time = datetime.min.time().replace(hour=9)
        
    # Adjust for today if time has passed
    if target_date == now.date() and target_time and target_time <= now.time() and 'сегодня' not in text:
        target_date += timedelta(days=1)
            
    if target_date == now.date() and target_time is None:
        return None

    final_dt = tz.localize(datetime.combine(target_date, target_time or now.time()))
    return final_dt.astimezone(pytz.utc)


def require_login(f):
    """Decorator to check for authentication and user existence"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('auth.login'))
        from app.models import User
        user = db.session.get(User, user_id)
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def format_datetime_for_user(dt, timezone_str='UTC'):
    """Formats datetime for the user, considering the timezone"""
    if dt is None:
        return ''
    try:
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return str(dt)