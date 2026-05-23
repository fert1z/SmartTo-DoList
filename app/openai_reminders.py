from __future__ import annotations

import html
import os
import logging
import time
from typing import Optional

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
