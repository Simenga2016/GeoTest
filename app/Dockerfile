# Базовый образ
FROM python:3.11-slim

# Установить рабочую директорию
WORKDIR /app

# Скопировать зависимости
COPY requirements.txt .

# Установить зависимости
RUN pip install -r requirements.txt

# Скопировать приложение
COPY . .

# Открыть порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
