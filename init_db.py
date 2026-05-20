#!/usr/bin/env python
"""Инициализация базы данных"""
from app import create_app, db

app = create_app()
with app.app_context():
    db.create_all()
    print("✓ База данных инициализирована успешно")
