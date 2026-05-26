from __future__ import annotations

import html
import os
import logging
import time
from typing import Optional
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
# Max retries for OpenAI API calls (exponential backoff)
OPENAI_MAX_RETRIES = 3
OPENAI_TIMEOUT = 20
OPENAI_MAX_CONTENT_LENGTH = 500  # Limit reminder text length


def _openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key


def _openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def parse_natural_time_with_openai(text: str, user_timezone: str = 'UTC') -> Optional[datetime]:
    """
    Parses a natural language string into a UTC datetime object using OpenAI.
    Returns None if parsing fails.
    """
    api_key = _openai_api_key()
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set. Cannot parse natural time.")
        return None
        
    if not text:
        return None

    model = _openai_model()
    now_utc = datetime.now(timezone.utc)
    
    prompt = (
        "You are an expert at extracting dates and times from natural language Russian text and converting them into strict ISO 8601 format in UTC.\n\n"
        "RULES:\n"
        "1. The user's local timezone is {user_timezone}.\n"
        "2. The current exact UTC time is {now_utc_iso}.\n"
        "3. You must interpret the user's text relative to this current time and their timezone.\n"
        "4. Output ONLY the calculated ISO 8601 datetime string in UTC format (e.g., 'YYYY-MM-DDTHH:MM:SS+00:00').\n"
        "5. If the time is not specified (e.g., just 'завтра'), assume 09:00 AM in the user's local timezone.\n"
        "6. If the text does not contain any recognizable time or date, output ONLY the word 'None'.\n"
        "7. Do not include markdown formatting, backticks, or any explanations.\n\n"
        "EXAMPLES:\n"
        "- Current UTC: 2026-05-25T08:00:00+00:00, User TZ: Europe/Moscow (UTC+3, so local is 11:00). Query: 'завтра в 10' -> Result: 2026-05-26T07:00:00+00:00\n"
        "- Current UTC: 2026-05-25T08:00:00+00:00, User TZ: Europe/Moscow. Query: 'через 2 часа' -> Result: 2026-05-25T10:00:00+00:00\n"
        "- Current UTC: 2026-05-25T08:00:00+00:00, User TZ: UTC. Query: 'купить хлеб' -> Result: None\n\n"
        "ACTUAL REQUEST:\n"
        "Query: '{text}' -> Result: "
    ).format(user_timezone=user_timezone, now_utc_iso=now_utc.isoformat(), text=text)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise time parsing engine. You output only ISO 8601 strings or 'None'."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 30,
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=OPENAI_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        result_text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()

        logger.info("OpenAI raw response: '%s'", result_text)

        if result_text and result_text.lower() != 'none':
            # Clean up potential markdown backticks
            result_text = result_text.replace('`', '').strip()
            # OpenAI might return 'Z' or '+00:00'. Standardize by replacing 'Z'.
            if result_text.endswith('Z'):
                result_text = result_text[:-1] + '+00:00'
            
            # Additional validation: check if it's a valid ISO format
            parsed_date = datetime.fromisoformat(result_text)
            
            # Ensure it has timezone info, default to UTC if missing
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                
            return parsed_date
        else:
             logger.warning("OpenAI returned 'None' for input: '%s'", text)
            
    except (requests.RequestException, ValueError, IndexError) as e:
        logger.error("OpenAI time parsing failed for input '%s': %s", text, str(e))
    
    return None


def generate_reminder_text(
    *,
    title: str,
    description: Optional[str],
    due_iso: Optional[str],
    priority: Optional[str],
) -> str:
    """
    Generate short reminder text for Telegram.
    
    Implements retry logic with exponential backoff.
    Never raises exceptions — always returns a safe fallback on error.
    """
    api_key = _openai_api_key()
    if not api_key:
        return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."

    model = _openai_model()

    desc_part = description.strip() if description else ""
    due_part = due_iso or ""

    prompt = (
        "Ты ассистент по умным напоминаниям.\n"
        "Сгенерируй ОЧЕНЬ короткое (1-2 предложения) дружелюбное сообщение для Telegram:\n"
        "- на русском\n"
        "- без эмодзи, если не попросили\n"
        "- упомяни название задачи\n"
        "- если есть описание/дедлайн/приоритет — аккуратно используй\n"
        "- тон: деловой, но поддерживающий\n\n"
        f"Название: {title}\n"
        f"Описание: {desc_part}\n"
        f"Дедлайн: {due_part}\n"
        f"Приоритет: {priority or ''}\n\n"
        "Текст сообщения:"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 120,
    }

    # Retry logic with exponential backoff
    for attempt in range(OPENAI_MAX_RETRIES):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=OPENAI_TIMEOUT,
            )
            
            if r.status_code == 429:  # Rate limit
                wait_seconds = min(2 ** attempt, 60)  # Exponential backoff
                logger.warning("OpenAI rate limit hit, retrying in %d seconds", wait_seconds)
                time.sleep(wait_seconds)
                continue
            
            if r.status_code >= 500:  # Server error, retry
                wait_seconds = min(2 ** attempt, 30)
                logger.warning("OpenAI server error %s, retrying in %d seconds", r.status_code, wait_seconds)
                time.sleep(wait_seconds)
                continue
            
            if r.status_code >= 400:  # Client error, don't retry
                logger.warning("OpenAI error %s: %s", r.status_code, r.text[:200])
                return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."

            data = r.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            text = (text or "").strip()
            
            # Validate and escape output
            if not text or len(text) > OPENAI_MAX_CONTENT_LENGTH:
                logger.warning("OpenAI returned invalid content length")
                return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."
            
            # Escape HTML to prevent injection in Telegram
            text = html.escape(text)
            return text
            
        except requests.Timeout:
            logger.warning("OpenAI request timeout on attempt %d/%d", attempt + 1, OPENAI_MAX_RETRIES)
            if attempt < OPENAI_MAX_RETRIES - 1:
                wait_seconds = min(2 ** attempt, 20)
                time.sleep(wait_seconds)
        except requests.RequestException as e:
            logger.warning("OpenAI request failed on attempt %d/%d: %s", attempt + 1, OPENAI_MAX_RETRIES, str(e))
            if attempt < OPENAI_MAX_RETRIES - 1:
                wait_seconds = min(2 ** attempt, 20)
                time.sleep(wait_seconds)
        except Exception:
            logger.exception("Unexpected error in OpenAI call on attempt %d/%d", attempt + 1, OPENAI_MAX_RETRIES)
            if attempt < OPENAI_MAX_RETRIES - 1:
                time.sleep(1)
    
    # All retries exhausted
    logger.error("OpenAI request failed after %d attempts", OPENAI_MAX_RETRIES)
    return "Напоминание: пора заняться задачей. Проверьте дедлайн и приоритет."