"""
Модуль для взаимодействия с различными AI-провайдерами (OpenAI, Google Gemini).
"""
from __future__ import annotations

import os
import logging
from typing import Optional
from datetime import datetime, timezone
import requests
import google.generativeai as genai

logger = logging.getLogger(__name__)

# --- OpenAI Provider ---

def parse_natural_time_with_openai(text: str, user_timezone: str, api_key: str) -> Optional[datetime]:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    now_utc = datetime.now(timezone.utc)
    
    prompt = (
        "You are a time parsing assistant. Your task is to convert a natural language query about time into a precise ISO 8601 datetime string in UTC.\n"
        "The user's local timezone is {user_timezone}.\n"
        "The current UTC time is: {now_utc_iso}.\n"
        "The user's query is: '{text}'.\n"
        "Based on this, what is the exact UTC datetime the user is referring to?\n"
        "Respond ONLY with the ISO 8601 string (e.g., 'YYYY-MM-DDTHH:MM:SS+00:00') and nothing else. If the query is not a valid time, respond with 'None'."
    ).format(user_timezone=user_timezone, now_utc_iso=now_utc.isoformat(), text=text)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 50,
    }

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        result_text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        logger.info("OpenAI raw response: '%s'", result_text)

        if result_text and result_text.lower() != 'none':
            if result_text.endswith('Z'):
                result_text = result_text[:-1] + '+00:00'
            return datetime.fromisoformat(result_text)
    except Exception as e:
        logger.error("OpenAI API call failed: %s", str(e))
    
    return None

# --- Google Gemini Provider ---

def parse_natural_time_with_gemini(text: str, user_timezone: str, api_key: str) -> Optional[datetime]:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    now_utc = datetime.now(timezone.utc)

    prompt = (
        "Ты — эксперт по извлечению даты и времени из текста на естественном русском языке. Твоя задача — преобразовать запрос в строгий формат ISO 8601 в UTC.\n\n"
        "ПРАВИЛА:\n"
        "1. Часовой пояс пользователя: {user_timezone}.\n"
        "2. Текущее точное время в UTC: {now_utc_iso}.\n"
        "3. Ты должен интерпретировать запрос пользователя относительно текущего времени и его часового пояса.\n"
        "4. В ответе должна быть ТОЛЬКО строка в формате ISO 8601 (например, 'YYYY-MM-DDTHH:MM:SS+00:00').\n"
        "5. Если время не указано (например, 'завтра'), используй 09:00 утра по времени пользователя.\n"
        "6. Если в тексте нет даты или времени, верни ТОЛЬКО слово 'None'.\n"
        "7. Никаких объяснений, только результат.\n\n"
        "ЗАПРОС: '{text}' -> "
    ).format(user_timezone=user_timezone, now_utc_iso=now_utc.isoformat(), text=text)

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        logger.info("Gemini raw response: '%s'", result_text)

        if result_text and result_text.lower() != 'none':
            if result_text.endswith('Z'):
                result_text = result_text[:-1] + '+00:00'
            return datetime.fromisoformat(result_text)
    except Exception as e:
        logger.error("Gemini API call failed: %s", str(e))
        
    return None