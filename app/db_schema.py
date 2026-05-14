"""Лёгкие миграции без Alembic: добавление колонок к существующим таблицам SQLite/Postgres."""
from sqlalchemy import inspect, text


def apply_schema_migrations(db):
    bind = db.engine
    inspector = inspect(bind)
    dialect = bind.dialect.name

    tables = inspector.get_table_names()
    if 'users' in tables:
        cols = {c['name'] for c in inspector.get_columns('users')}
        if 'telegram_user_id' not in cols:
            col_type = 'BIGINT' if dialect != 'sqlite' else 'INTEGER'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN telegram_user_id {col_type}'))
            with bind.begin() as conn:
                conn.execute(
                    text(
                        'CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_user_id '
                        'ON users (telegram_user_id)'
                    )
                )
        if 'timezone' not in cols:
            with bind.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN timezone VARCHAR(32) DEFAULT 'UTC'"))

    if 'tasks' in tables:
        cols = {c['name'] for c in inspector.get_columns('tasks')}
        if 'notified_at' not in cols:
            col_type = 'TIMESTAMP WITH TIME ZONE' if dialect != 'sqlite' else 'TIMESTAMP'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE tasks ADD COLUMN notified_at {col_type}'))
        if 'completed_at' not in cols:
            col_type = 'TIMESTAMP WITH TIME ZONE' if dialect != 'sqlite' else 'TIMESTAMP'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE tasks ADD COLUMN completed_at {col_type}'))
