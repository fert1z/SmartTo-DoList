from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re

try:
    import dateparser
except ImportError:
    dateparser = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def _get_openai_client():
    from flask import current_app
    api_key = current_app.config.get('OPENAI_API_KEY')
    if OpenAI and api_key:
        return OpenAI(api_key=api_key)
    return None

DEFAULT_TIMEZONE = 'UTC'
COMMON_TIMEZONES = [
    'UTC',
    'Europe/Moscow',
    'Europe/Kiev',
    'Europe/Minsk',
    'Europe/London',
    'Europe/Berlin',
    'Asia/Yekaterinburg',
    'Asia/Novosibirsk',
    'Asia/Vladivostok',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'America/New_York',
    'America/Los_Angeles',
    'Asia/Kolkata',
    'Australia/Sydney',
]

PRIORITY_KEYWORDS = {
    'high': [
        r'\bсрочно\b',
        r'\bсрочно\b',
        r'\bважно\b',
        r'\bкритично\b',
        r'\bнемедленно\b',
        r'\bсрочно!\b',
        r'\bдо завтра\b',
        r'\bдо конца дня\b',
    ],
    'low': [
        r'\bпозже\b',
        r'\bкогда-нибудь\b',
        r'\bне обязательно\b',
        r'\bпо желанию\b',
        r'\bможно позже\b',
    ],
}

CATEGORY_KEYWORDS = {
    'work': [r'\bработа\b', r'\bпроект\b', r'\bсрочный\b', r'\bвстреча\b', r'\bдело\b'],
    'study': [r'\bучеба\b', r'\bкурс\b', r'\bлекция\b', r'\bдз\b', r'\bэкзамен\b'],
}

DATE_FORMATS = (
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y',
    '%d.%m %H:%M',
    '%d.%m',
)

NATURAL_DATE_PATTERNS = [
    (re.compile(r'^сегодня\s*(.*)$', re.IGNORECASE), 0),
    (re.compile(r'^завтра\s*(.*)$', re.IGNORECASE), 1),
    (re.compile(r'^послезавтра\s*(.*)$', re.IGNORECASE), 2),
]


def safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _apply_timezone(dt: datetime, tz_name: str) -> datetime:
    if dt is None:
        return None
    tz = safe_zoneinfo(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def parse_due_date(raw: str, timezone_name: str = DEFAULT_TIMEZONE) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    normalized = s.lower().replace('ё', 'е').strip()
    now = datetime.now(timezone.utc).astimezone(safe_zoneinfo(timezone_name))

    for pattern, offset_days in NATURAL_DATE_PATTERNS:
        match = pattern.match(normalized)
        if match:
            time_part = match.group(1).strip()
            due_date_obj = (now + timedelta(days=offset_days)).date()
            if not time_part:
                due_date_time = datetime.combine(due_date_obj, datetime.min.time().replace(hour=18))
                return due_date_time.replace(tzinfo=safe_zoneinfo(timezone_name)).astimezone(timezone.utc)
            s = f'{due_date_obj.isoformat()} {time_part}'
            break

    if normalized.startswith('через'):
        match = re.match(r'через\s*(\d+)\s*(дней|дня|часов|часа|минут|минуты)', normalized)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit.startswith('дн'):
                return (datetime.now(timezone.utc) + timedelta(days=amount)).astimezone(timezone.utc)
            if unit.startswith('час'):
                return (datetime.now(timezone.utc) + timedelta(hours=amount)).astimezone(timezone.utc)
            if unit.startswith('мин'):
                return (datetime.now(timezone.utc) + timedelta(minutes=amount)).astimezone(timezone.utc)

    # Продвинутый парсинг естественного языка (если установлена библиотека dateparser)
    if dateparser:
        parsed = dateparser.parse(s, settings={'TIMEZONE': timezone_name, 'RETURN_AS_TIMEZONE_AWARE': True, 'PREFER_DATES_FROM': 'future'})
        if parsed:
            return parsed.astimezone(timezone.utc)

    s = s.replace('Z', '+00:00')
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(s, fmt)
            if fmt == '%d.%m':
                parsed = parsed.replace(year=now.year)
            if fmt == '%d.%m %H:%M':
                parsed = parsed.replace(year=now.year)
            parsed = parsed.replace(tzinfo=safe_zoneinfo(timezone_name))
            # If the parsed date is in the past, assume next year
            if parsed.date() < now.date():
                try:
                    parsed = parsed.replace(year=parsed.year + 1)
                except ValueError:
                    # Handle leap year edge case: Feb 29 in non-leap year
                    if parsed.month == 2 and parsed.day == 29:
                        parsed = parsed.replace(year=parsed.year + 1, month=2, day=28)
                    else:
                        # Fallback: shouldn't happen
                        parsed = parsed.replace(year=parsed.year + 1)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=safe_zoneinfo(timezone_name))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def format_datetime_for_user(value: datetime | None, timezone_name: str = DEFAULT_TIMEZONE) -> str | None:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    # Возвращаем в UTC с 'Z' для корректного парсинга в JS как UTC
    return value.isoformat() + 'Z'


def suggest_task_priority(title: str | None, description: str | None) -> str:
    text = ' '.join(filter(None, [title, description or ''])).lower()
    if not text:
        return 'medium'
        
    # Использование OpenAI для умного определения приоритета
    client = _get_openai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a task priority classifier. Reply ONLY with one word: 'high', 'medium', or 'low'."},
                    {"role": "user", "content": f"Task: {text}"}
                ],
                max_tokens=5,
                temperature=0.3
            )
            res = response.choices[0].message.content.strip().lower()
            if res in ['high', 'medium', 'low']:
                return res
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(f"OpenAI priority classification failed: {e}")
            pass

    for priority, patterns in PRIORITY_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return priority
    return 'medium'


def infer_task_category(title: str | None, description: str | None) -> str:
    text = ' '.join(filter(None, [title, description or ''])).lower()

    # Использование OpenAI для умного определения категории
    client = _get_openai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a task category classifier. Classify the task into one of these categories: 'work', 'study', 'personal', 'shopping', 'health'. Reply ONLY with the category word."},
                    {"role": "user", "content": f"Task: {text}"}
                ],
                max_tokens=5,
                temperature=0.3
            )
            res = response.choices[0].message.content.strip().lower()
            if res in ['work', 'study', 'personal', 'shopping', 'health']:
                return res
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(f"OpenAI category classification failed: {e}")
            pass

    for category, patterns in CATEGORY_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return category
    return 'personal'
