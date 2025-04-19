FROM python:3.11-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Сборка статических файлов
RUN python manage.py collectstatic --noinput

# Создание пользователя для запуска приложения
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Запуск приложения через Gunicorn
CMD ["gunicorn", "polesharing.wsgi:application", "--bind", "0.0.0.0:8000"] 