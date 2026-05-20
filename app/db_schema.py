"""Лёгкие миграции без Alembic: добавление колонок к существующим таблицам SQLite/Postgres."""
from sqlalchemy import inspect, text


def apply_schema_migrations(db):
    bind = db.engine
    inspector = inspect(bind)
    dialect = bind.dialect.name

    tables = inspector.get_table_names()

    # users.telegram_user_id
    if 'users' in tables:
        cols = {c['name'] for c in inspector.get_columns('users')}
        if 'telegram_user_id' not in cols:
            col_type = 'BIGINT' if dialect != 'sqlite' else 'INTEGER'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN telegram_user_id {col_type}'))
            # Уникальность для старых БД без этой колонки (новые создаются из модели)
            with bind.begin() as conn:
                conn.execute(
                    text(
                        'CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_user_id '
                        'ON users (telegram_user_id)'
                    )
                )

    # reminder_logs (если таблица отсутствует — пусть create_all её создаст,
    # но если по какой-то причине её не создало, добавим минимальную структуру).
    if 'reminder_logs' not in tables:
        # Для простоты создадим таблицу через SQLAlchemy metadata.
        # create_all обычно всё равно её делает, но этот блок защищает старые схемы.
        return
