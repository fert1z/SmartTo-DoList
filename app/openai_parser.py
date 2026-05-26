import os
import json
import logging
from typing import Optional
from datetime import datetime, timezone
import requests
import locale

logger = logging.getLogger(__name__)

OPENAI_TIMEOUT = 20
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

def _openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()

def _openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL

def parse_natural_time_with_openai(text: str, user_timezone: str = 'UTC') -> Optional[datetime]:
    """
    Парсит естественный язык в дату через OpenAI, используя продвинутый промпт и JSON вывод.
    """
    api_key = _openai_api_key()
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set. Cannot parse natural time.")
        return None
        
    if not text:
        return None

    try:
        # Пытаемся установить русскую локаль для красивого вывода даты, 
        # но если ее нет, просто форматируем руками
        now = datetime.now(timezone.utc) # Важно: для GPT будем давать UTC, но говорить, что это локальное время, 
        # либо давать локальное. Лучше давать точное UTC и просить вернуть UTC.
        
        # Передаем точное время в UTC, чтобы избежать путаницы
        now_utc_str = now.strftime("%A, %d %B %Y года, %H:%M UTC")

        prompt = f"""Ты — специализированный ИИ-модуль для парсинга даты и времени из текстовых напоминаний. Твоя задача — переводить естественный язык пользователя в строгий формат даты и времени для последующей обработки скриптом.

### КОНТЕКСТ (Точка отсчета)
Для правильного расчета тебе ВСЕГДА необходимы текущие дата и время. 
Входные данные будут поступать в формате:
- Текущее время (в UTC): {now_utc_str}
- Часовой пояс пользователя: {user_timezone}
- Текст пользователя: {text}

ВАЖНО: Результат (calculated_timestamp) должен быть возвращен СТРОГО в часовом поясе UTC. Если пользователь просит "завтра в 10 утра", а его пояс UTC+3, ты должен вернуть завтрашний день и 07:00:00.

### ПРАВИЛА РАСЧЕТА И КАТЕГОРИИ РЕЧИ:

1. Относительные смещения (Интервалы):
- "Через X часов/минут/дней/недель/месяцев" — строго прибавляй X к текущему времени.
- "Через полчаса" — прибавляй 30 минут.
- "Через полтора часа" — прибавляй 90 минут.
- "Через четверть часа" — прибавляй 15 минут.
- "Час назад / вчера" — вычитай время (используй только если контекст подразумевает запись прошедшего события).

2. Абстрактные дни:
- "Сегодня" — текущая дата пользователя.
- "Завтра" — текущая дата пользователя + 1 день.
- "Послезавтра" / "Через день" — текущая дата пользователя + 2 дня.

3. Дни недели и недели:
- "В [день недели]" (например, "в среду") — находи ближнюю следующую среду. Если сегодня среда и указанное время уже прошло, бери среду на следующей неделе.
- "В следующий(-ую) [день недели]" / "На следующей неделе в [день недели]" — строго ищи этот день на следующей календарной неделе.
- "На выходных" — если сегодня будний день, планируй на ближайшую субботу. Если сегодня суббота или воскресенье — на текущий день.

4. Размытые временные промежутки (Дефолтные значения ПО ЛОКАЛЬНОМУ ВРЕМЕНИ):
Если указан период суток, но не указан час, используй эти стандарты в ЛОКАЛЬНОМ времени пользователя (а в ответе верни переведенное в UTC):
- "Утром" / "С утра" -> 09:00:00
- "В обед" -> 13:00:00
- "Днем" -> 14:00:00
- "Вечером" / "Под вечер" -> 18:00:00
- "Ночью" -> 23:00:00
- Если указан только день, используй дефолтное рабочее время -> 09:00:00 локального времени.

5. Точные даты и праздники:
- "X [месяца]" (например, "1 сентября") — подставляй указанное число и месяц.
- Если год не указан и дата уже прошла, автоматически переноси на СЛЕДУЮЩИЙ год.

### ФОРМАТ ВЫВОДА:
Выводи результат СТРОГО в формате JSON. Никакого текста, только JSON.

{{
  "status": "success",
  "calculated_timestamp": "YYYY-MM-DD HH:MM:SS"
}}

Если текст невозможно распознать, верни:
{{
  "status": "error",
  "message": "Не удалось распознать время"
}}
"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": _openai_model(),
            "messages": [
                {"role": "system", "content": "You are a JSON-only time parsing API."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": { "type": "json_object" } # Принудительно требуем JSON
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=OPENAI_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"OpenAI API error {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        result_text = data['choices'][0]['message']['content'].strip()
        logger.info(f"OpenAI parsed result: {result_text}")
        
        result_json = json.loads(result_text)
        
        if result_json.get("status") == "success":
            ts_str = result_json.get("calculated_timestamp")
            if ts_str:
                # Парсим "YYYY-MM-DD HH:MM:SS" и добавляем UTC таймзону
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                return dt.replace(tzinfo=timezone.utc)
                
        return None
            
    except Exception as e:
        logger.error(f"Failed to parse time with OpenAI: {str(e)}")
        return None