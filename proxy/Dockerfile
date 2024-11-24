# Используем официальный базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями (если есть) и сам код
COPY requirements.txt ./
COPY proxy.py ./

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Указываем порт, который будет прослушиваться внутри контейнера
EXPOSE 5000

ENV PYTHONUNBUFFERED=1

# Запускаем сервер
CMD ["python", "proxy.py"]
