"""
Обработчики Telegram-бота: привязка аккаунта, список задач, добавление, выполнение, удаление.
Требуется переменная окружения TELEGRAM_BOT_TOKEN.
"""
from __future__ import annotations

import html
import io
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import telebot
from telebot import types

from app import create_app, db
from app.models import Task, TelegramLinkCode, User
from app.utils import parse_due_date, format_datetime_for_user, suggest_task_priority, infer_task_category

logger = logging.getLogger(__name__)

_app = None
bot: telebot.TeleBot | None = None

# Ожидание текста новой задачи после команды /add без аргументов
_pending_add_title: dict[int, bool] = {}

PAGE_SIZE = 5


def _clear_pending(uid: int):
    _pending_add_title.pop(uid, None)


def get_app():
    global _app
    if _app is None:
        _app = create_app(scheduler_enabled=False)
    return _app


def get_bot() -> telebot.TeleBot:
    global bot
    if bot is None:
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        if not token:
            raise RuntimeError('Задайте TELEGRAM_BOT_TOKEN в окружении или в .env')
        bot = telebot.TeleBot(token, parse_mode='HTML')
    return bot


def _user_for_telegram(telegram_user_id: int) -> User | None:
    return User.query.filter_by(telegram_user_id=telegram_user_id).first()


def _require_user(message) -> User | None:
    u = _user_for_telegram(message.from_user.id)
    if u:
        return u
    get_bot().reply_to(
        message,
        'Аккаунт не привязан. Откройте веб-приложение → Настройки → получите код и отправьте:\n'
        '<code>/link ВАШ_КОД</code>',
    )
    return None


def _get_user_timezone(user: User) -> str:
    try:
        return user.timezone or 'UTC'
    except Exception:
        return 'UTC'


def _format_task_due(task: Task, user: User) -> str:
    if not task.due_date:
        return 'без срока'
    return format_datetime_for_user(task.due_date, _get_user_timezone(user))


def _recognize_voice_text(file_bytes: bytes) -> str | None:
    try:
        from pydub import AudioSegment
        import speech_recognition as sr
    except ImportError:
        return None

    try:
        audio = AudioSegment.from_file(io.BytesIO(file_bytes), format='ogg')
        audio = audio.set_channels(1).set_frame_rate(16000)
        wav_io = io.BytesIO()
        audio.export(wav_io, format='wav')
        wav_io.seek(0)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language='ru-RU')
    except Exception:
        return None


def _cleanup_expired_codes():
    TelegramLinkCode.query.filter(TelegramLinkCode.expires_at < datetime.now(timezone.utc)).delete()
    db.session.commit()


def register_handlers() -> telebot.TeleBot:
    b = get_bot()

    @b.message_handler(commands=['start'])
    def cmd_start(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            text = (
                '<b>SmartTo-DoList</b>\n\n'
                'Команды:\n'
                '/help — все команды\n'
                '/link КОД — привязать аккаунт (код в веб-настройках)\n'
                '/tasks — список задач\n'
                '/remind — напомнить о ближайших задачах\n'
                '/add текст — новая задача\n'
                '/done НОМЕР — отметить выполненной\n'
                '/del НОМЕР — удалить\n'
                '/stats — статистика\n'
            )
            b.reply_to(message, text)

    @b.message_handler(commands=['help'])
    def cmd_help(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            text = (
                '<b>Команды</b>\n'
                '/link <code>КОД</code> — связать Telegram с аккаунтом сайта\n'
                '/tasks — показать активные задачи (кнопки ниже сообщения)\n'
                '/remind — напомнить о ближайших задачах\n'
                '/add <i>название</i> — добавить задачу (или /add и затем текст сообщением)\n'
                '/done <i>id</i> — выполнить задачу по номеру из списка /tasks\n'
                '/del <i>id</i> — удалить задачу\n'
                '/stats — сколько задач всего и сколько выполнено\n'
                '/unlink — отвязать этот Telegram от аккаунта\n'
            )
            b.reply_to(message, text)

    @b.message_handler(commands=['link'])
    def cmd_link(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            parts = (message.text or '').split(maxsplit=1)
            if len(parts) < 2:
                b.reply_to(message, 'Использование: <code>/link КОД</code> (код из веб-настроек)')
                return
            code = parts[1].strip().upper()
            if not re.match(r'^[A-F0-9]{8}$', code):
                b.reply_to(message, 'Неверный формат кода. Нужен 8 символов (буквы и цифры).')
                return

            _cleanup_expired_codes()
            row = TelegramLinkCode.query.filter_by(code=code).first()
            if not row or row.expires_at < datetime.now(timezone.utc):
                b.reply_to(message, 'Код не найден или истёк. Сгенерируйте новый в настройках сайта.')
                return

            tg_id = message.from_user.id
            existing = User.query.filter_by(telegram_user_id=tg_id).first()
            if existing and existing.id != row.user_id:
                b.reply_to(
                    message,
                    'Этот Telegram уже привязан к другому аккаунту. Отвяжите его в настройках того аккаунта.',
                )
                return

            user = User.query.get(row.user_id)
            if not user:
                b.reply_to(message, 'Ошибка: пользователь не найден.')
                return

            if user.telegram_user_id and user.telegram_user_id != tg_id:
                user.telegram_user_id = None
                db.session.flush()

            user.telegram_user_id = tg_id
            TelegramLinkCode.query.filter_by(user_id=user.id).delete()
            db.session.commit()

            b.reply_to(message, f'Аккаунт <b>{html.escape(user.username)}</b> успешно привязан.')

    @b.message_handler(commands=['unlink'])
    def cmd_unlink(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            u = _user_for_telegram(message.from_user.id)
            if not u:
                b.reply_to(message, 'Telegram не был привязан.')
                return
            u.telegram_user_id = None
            TelegramLinkCode.query.filter_by(user_id=u.id).delete()
            db.session.commit()
            b.reply_to(message, 'Telegram отвязан. Вы можете привязать аккаунт снова через сайт.')

    @b.message_handler(commands=['stats'])
    def cmd_stats(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            total = Task.query.filter_by(user_id=user.id).count()
            done = Task.query.filter_by(user_id=user.id, status='completed').count()
            b.reply_to(
                message,
                f'Всего задач: <b>{total}</b>\nВыполнено: <b>{done}</b>\nАктивных: <b>{total - done}</b>',
            )

    def _send_task_page(chat_id, user: User, page: int, message_id=None):
        q = (
            Task.query.filter_by(user_id=user.id)
            .filter(Task.status != 'completed')
            .order_by(Task.created_at.desc())
        )
        total = q.count()
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        chunk = q.offset(start).limit(PAGE_SIZE).all()

        lines = []
        for t in chunk:
            due = _format_task_due(t, user)
            pr = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t.priority or '', '⚪')
            lines.append(
                f'{pr} <b>#{t.id}</b> {html.escape(t.title or "")} — {html.escape(t.category or "личное")} — {html.escape(due)}'
            )
        if not lines:
            body = 'Нет активных задач. Добавьте: <code>/add Название</code>'
        else:
            body = '\n'.join(lines) + f'\n\nСтр. {page + 1}/{pages} · всего активных: {total}'

        kb = types.InlineKeyboardMarkup(row_width=3)
        for t in chunk:
            kb.row(
                types.InlineKeyboardButton(text=f'✓{t.id}', callback_data=f'd:{t.id}'),
                types.InlineKeyboardButton(text=f'✕{t.id}', callback_data=f'x:{t.id}'),
                types.InlineKeyboardButton(text=f'⚡', callback_data=f'pr:{t.id}:high'),
                types.InlineKeyboardButton(text=f'🟡', callback_data=f'pr:{t.id}:medium'),
                types.InlineKeyboardButton(text=f'🟢', callback_data=f'pr:{t.id}:low')
            )
            kb.row(
                types.InlineKeyboardButton(text=f'W{t.id}', callback_data=f'cat:{t.id}:work'),
                types.InlineKeyboardButton(text=f'S{t.id}', callback_data=f'cat:{t.id}:study'),
                types.InlineKeyboardButton(text=f'P{t.id}', callback_data=f'cat:{t.id}:personal'),
            )
        nav_row = []
        if page > 0:
            nav_row.append(types.InlineKeyboardButton('◀', callback_data=f'p:{page - 1}'))
        if page < pages - 1:
            nav_row.append(types.InlineKeyboardButton('▶', callback_data=f'p:{page + 1}'))
        if nav_row:
            kb.row(*nav_row)

        if message_id:
            try:
                b.edit_message_text(body, chat_id=chat_id, message_id=message_id, reply_markup=kb)
            except Exception as e:
                logger.debug('edit_message_text: %s', e)
                b.send_message(chat_id, body, reply_markup=kb)
        else:
            b.send_message(chat_id, body, reply_markup=kb)

    @b.message_handler(commands=['tasks'])
    def cmd_tasks(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            _send_task_page(message.chat.id, user, 0)

    @b.message_handler(commands=['remind'])
    def cmd_remind(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            now = datetime.now(timezone.utc)
            upcoming = (
                Task.query.filter_by(user_id=user.id)
                .filter(Task.status != 'completed')
                .filter(Task.due_date != None)
                .order_by(Task.due_date.asc())
                .limit(10)
                .all()
            )
            lines = []
            for task in upcoming:
                if task.due_date:
                    due_dt = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
                    delta = due_dt - now
                    status = '⛔ Просрочено' if task.is_overdue() else '⚠️ Скоро' if delta.total_seconds() <= 86400 else '⏳'
                    date_str = _format_task_due(task, user)
                    lines.append(f'{status} <b>#{task.id}</b> {html.escape(task.title or "")} — {date_str}')
            if not lines:
                b.reply_to(message, 'Нет ближайших задач с датой. Добавьте задачу со сроком или используйте /tasks.')
                return
            b.reply_to(message, '<b>Ближайшие задачи</b>\n' + '\n'.join(lines))

    @b.message_handler(commands=['add'])
    def cmd_add(message):
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            text = message.text or ''
            parts = text.split(maxsplit=1)
            if len(parts) >= 2 and parts[1].strip():
                _clear_pending(message.from_user.id)
            if len(parts) < 2 or not parts[1].strip():
                _pending_add_title[message.from_user.id] = True
                b.reply_to(message, 'Введите название задачи одним сообщением (до 200 символов):')
                return

            raw_text = parts[1].strip()
            due_dt = None
            title = raw_text
            if '|' in raw_text:
                title_candidate, due_candidate = raw_text.split('|', 1)
                title = title_candidate.strip()[:200]
                due_dt = parse_due_date(due_candidate.strip(), _get_user_timezone(user))

            if not title:
                b.reply_to(message, 'Пустой текст — задача не создана.')
                return

            priority = suggest_task_priority(title, None)
            category = infer_task_category(title, None)
            task = Task(title=title, due_date=due_dt, user_id=user.id, priority=priority, category=category)
            db.session.add(task)
            db.session.commit()
            response = f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}'
            if due_dt:
                response += f' · до {_format_task_due(task, user)}'
            b.reply_to(message, response)

    @b.message_handler(commands=['done'])
    def cmd_done(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            parts = (message.text or '').split()
            if len(parts) < 2 or not parts[1].isdigit():
                b.reply_to(message, 'Использование: <code>/done ID</code> (номер из списка /tasks)')
                return
            tid = int(parts[1])
            task = Task.query.filter_by(id=tid, user_id=user.id).first()
            if not task:
                b.reply_to(message, 'Задача не найдена.')
                return
            task.complete()
            db.session.commit()
            b.reply_to(message, f'Выполнено: #{tid} {html.escape(task.title)}')

    @b.message_handler(commands=['del'])
    def cmd_del(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            parts = (message.text or '').split()
            if len(parts) < 2 or not parts[1].isdigit():
                b.reply_to(message, 'Использование: <code>/del ID</code>')
                return
            tid = int(parts[1])
            task = Task.query.filter_by(id=tid, user_id=user.id).first()
            if not task:
                b.reply_to(message, 'Задача не найдена.')
                return
            title = task.title
            db.session.delete(task)
            db.session.commit()
            b.reply_to(message, f'Удалено: #{tid} {html.escape(title or "")}')

    @b.message_handler(content_types=['voice'])
    def handle_voice(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            if not message.voice:
                b.reply_to(message, 'Отправьте голосовое сообщение.')
                return
            # Проверка размера файла (макс 10MB для предотвращения OOM)
            if message.voice.file_size and message.voice.file_size > 10 * 1024 * 1024:
                b.reply_to(message, 'Файл слишком большой. Максимальный размер: 10MB.')
                return
            try:
                file_info = b.get_file(message.voice.file_id)
                file_bytes = b.download_file(file_info.file_path)
                text = _recognize_voice_text(file_bytes)
            except Exception:
                text = None
            if not text:
                b.reply_to(
                    message,
                    'Не удалось распознать голосовое сообщение. Убедитесь, что оно короткое и говорите ясно.',
                )
                return
            title = text.strip()[:200]
            priority = suggest_task_priority(title, None)
            category = infer_task_category(title, None)
            task = Task(title=title, user_id=user.id, priority=priority, category=category)
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена голосом: <b>#{task.id}</b> {html.escape(title)}')

    @b.callback_query_handler(func=lambda c: True)
    def on_callback(call):
        _clear_pending(call.from_user.id)
        with get_app().app_context():
            user = _user_for_telegram(call.from_user.id)
            if not user:
                try:
                    b.answer_callback_query(call.id, 'Сначала привяжите аккаунт: /link', show_alert=True)
                except Exception:
                    pass
                return
            data = call.data or ''
            if data.startswith('p:'):
                page = int(data.split(':')[1])
                _send_task_page(call.message.chat.id, user, page, call.message.message_id)
                try:
                    b.answer_callback_query(call.id)
                except Exception:
                    pass
                return
            if data.startswith('d:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    task.complete()
                    db.session.commit()
                    try:
                        b.answer_callback_query(call.id, 'Готово')
                    except Exception:
                        pass
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    try:
                        b.answer_callback_query(call.id, 'Не найдено')
                    except Exception:
                        pass
                return
            if data.startswith('x:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    db.session.delete(task)
                    db.session.commit()
                    try:
                        b.answer_callback_query(call.id, 'Удалено')
                    except Exception:
                        pass
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    try:
                        b.answer_callback_query(call.id, 'Не найдено')
                    except Exception:
                        pass
                return
            if data.startswith('pr:'):
                _, tid_str, priority = data.split(':', 2)
                tid = int(tid_str)
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task and priority in ('low', 'medium', 'high'):
                    task.priority = priority
                    db.session.commit()
                    try:
                        b.answer_callback_query(call.id, f'Приоритет обновлён: {priority}')
                    except Exception:
                        pass
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    try:
                        b.answer_callback_query(call.id, 'Не найдено или неверный приоритет')
                    except Exception:
                        pass
                return
            if data.startswith('cat:'):
                _, tid_str, category = data.split(':', 2)
                tid = int(tid_str)
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task and category in ('personal', 'work', 'study'):
                    task.category = category
                    db.session.commit()
                    try:
                        b.answer_callback_query(call.id, f'Категория обновлена: {category}')
                    except Exception:
                        pass
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    try:
                        b.answer_callback_query(call.id, 'Не найдено или неверная категория')
                    except Exception:
                        pass
                return
            if data.startswith('snooze:'):
                _, tid_str, minutes = data.split(':', 2)
                tid = int(tid_str)
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    task.due_date = datetime.now(timezone.utc) + timedelta(minutes=int(minutes))
                    task.notified_at = None # Чтобы планировщик сработал снова
                    db.session.commit()
                    try:
                        b.answer_callback_query(call.id, f'Отложено на {minutes} мин')
                    except Exception:
                        pass
                    b.edit_message_text(f"Задача #{tid} отложена", call.message.chat.id, call.message.message_id)
                else:
                    try:
                        b.answer_callback_query(call.id, 'Задача не найдена')
                    except Exception:
                        pass
                return
            try:
                b.answer_callback_query(call.id)
            except Exception:
                pass

    @b.message_handler(content_types=['text'], func=lambda m: m.chat.type == 'private')
    def on_plain_text(message):
        uid = message.from_user.id
        if uid not in _pending_add_title:
            return
        del _pending_add_title[uid]
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            title = (message.text or '').strip()[:200]
            if not title:
                b.reply_to(message, 'Пустой текст — задача не создана.')
                return
            priority = suggest_task_priority(title, None)
            category = infer_task_category(title, None)
            task = Task(title=title, user_id=user.id, priority=priority, category=category)
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}')

    @b.message_handler(func=lambda message: True)
    def clear_pending_general(message):
        _clear_pending(message.from_user.id)

    return b


def run_polling():
    logging.basicConfig(level=logging.INFO)
    try:
        from dotenv import load_dotenv
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        load_dotenv(os.path.join(root, '.env'))
    except ImportError:
        pass
    b = register_handlers()
    logger.info('Бот запущен (long polling). Остановка: Ctrl+C')
    b.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
