"""Лёгкие миграции без Alembic: добавление колонок к существующим таблицам SQLite/Postgres."""
from sqlalchemy import inspect, text


def apply_schema_migrations(db):
    bind = db.engine
    inspector = inspect(bind)
    dialect = bind.dialect.name

    tables = inspector.get_table_names()

    # users
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
                
        if 'is_email_confirmed' not in cols:
            col_type = 'BOOLEAN' if dialect != 'sqlite' else 'INTEGER'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN is_email_confirmed {col_type} NOT NULL DEFAULT TRUE'))
                
        if 'email_confirmed_at' not in cols:
            col_type = 'TIMESTAMP WITHOUT TIME ZONE' if dialect == 'postgresql' else 'DATETIME'
            with bind.begin() as conn:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN email_confirmed_at {col_type}'))
        
        if dialect == 'postgresql':
            with bind.begin() as conn:
                conn.execute(text('ALTER TABLE users ALTER COLUMN password TYPE VARCHAR(256)'))

    # tasks - исправляем старые значения в нижнем регистре на верхний
    if 'tasks' in tables:
        if dialect == 'postgresql':
            with bind.begin() as conn:
                # Обновляем значения перед изменением типа столбца, если это необходимо
                conn.execute(text("UPDATE tasks SET priority = UPPER(priority) WHERE priority IN ('low', 'medium', 'high')"))
                conn.execute(text("UPDATE tasks SET status = UPPER(status) WHERE status IN ('pending', 'in_progress', 'completed')"))
    
    # reminder_logs
    if 'reminder_logs' not in tables:
        return