import os
import logging
from typing import Optional
from datetime import datetime, timezone
import google.generativeai as genai

logger = logging.getLogger(__name__)


def _gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def parse_natural_time_with_gemini(text: str, user_timezone: str = 'UTC') -> Optional[datetime]:
    """
    Parses a natural language string into a UTC datetime object using Google Gemini.
    Returns None if parsing fails.
    """
    api_key = _gemini_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Cannot parse natural time.")
        return None
        
    if not text:
        return None

    try:
        genai.configure(api_key=api_key)
        # Использование актуальной стабильной модели
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        now_utc = datetime.now(timezone.utc)
        
        prompt = (
            "You are an expert at extracting dates and times from natural language Russian text and converting them into strict ISO 8601 format in UTC.\n\n"
            "RULES:\n"
            f"1. The user's local timezone is {user_timezone}.\n"
            f"2. The current exact UTC time is {now_utc.isoformat()}.\n"
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
            f"Query: '{text}' -> Result: "
        )

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
            )
        )
        
        result_text = response.text.strip()
        logger.info("Gemini raw response: '%s'", result_text)

        if result_text and result_text.lower() != 'none':
            # Очистка от маркдауна и переносов строк
            result_text = result_text.replace('`', '').strip()
            if result_text.endswith('Z'):
                result_text = result_text[:-1] + '+00:00'
            
            parsed_date = datetime.fromisoformat(result_text)
            
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                
            return parsed_date
        else:
            logger.warning("Gemini returned 'None' for input: '%s'", text)
            
    except Exception as e:
        logger.error("Gemini time parsing failed for input '%s': %s", text, str(e))
    
    return None
