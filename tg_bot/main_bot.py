"""
Обработчики Telegram-бота: привязка аккаунта, список задач, добавление, выполнение, удаление.
Требуется переменная окружения TELEGRAM_BOT_TOKEN.
"""
from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime

import telebot
from telebot import types

from app import create_app, db
from app.models import Task, TelegramLinkCode, User

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
        _app = create_app()
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


def _cleanup_expired_codes():
    TelegramLinkCode.query.filter(TelegramLinkCode.expires_at < datetime.utcnow()).delete()
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
            if not row or row.expires_at < datetime.utcnow():
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
        tasks = q.all()
        total = len(tasks)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        chunk = tasks[start : start + PAGE_SIZE]

        lines = []
        for t in chunk:
            due = ''
            if t.due_date:
                due = f' · до {t.due_date.strftime("%d.%m %H:%M")}'
            pr = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t.priority or '', '⚪')
            lines.append(
                f'{pr} <b>#{t.id}</b> {html.escape(t.title or "")}{html.escape(due)}'
            )
        if not lines:
            body = 'Нет активных задач. Добавьте: <code>/add Название</code>'
        else:
            body = '\n'.join(lines) + f'\n\nСтр. {page + 1}/{pages} · всего активных: {total}'

        kb = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        for t in chunk:
            buttons.append(
                types.InlineKeyboardButton(text=f'✓{t.id}', callback_data=f'd:{t.id}')
            )
            buttons.append(
                types.InlineKeyboardButton(text=f'✕{t.id}', callback_data=f'x:{t.id}')
            )
        if buttons:
            kb.add(*buttons)
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
            now = datetime.utcnow()
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
                    delta = task.due_date - now
                    status = '⛔ Просрочено' if task.is_overdue() else '⚠️ Скоро' if delta.total_seconds() <= 86400 else '⏳'
                    date_str = task.due_date.strftime('%d.%m %H:%M')
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
            title = parts[1].strip()[:200]
            task = Task(title=title, user_id=user.id, priority='medium')
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}')

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
                b.answer_callback_query(call.id)
                return
            if data.startswith('d:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    task.complete()
                    db.session.commit()
                    b.answer_callback_query(call.id, 'Готово')
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    b.answer_callback_query(call.id, 'Не найдено')
                return
            if data.startswith('x:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    db.session.delete(task)
                    db.session.commit()
                    b.answer_callback_query(call.id, 'Удалено')
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    b.answer_callback_query(call.id, 'Не найдено')
                return
            b.answer_callback_query(call.id)

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
            task = Task(title=title, user_id=user.id, priority='medium')
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}')

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
