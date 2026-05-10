import sys
import os

# Добавляем путь к backend, чтобы импорты работали
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine

print(f"Connecting to: {engine.url}")

try:
    with engine.connect() as conn:
        print("✅ DATABASE CONNECTION SUCCESSFUL! (Подключение к БД успешно!)")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED: {e}")