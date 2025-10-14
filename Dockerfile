# Базовый образ
FROM python:3.12

# Рабочая директория внутри контейнера
WORKDIR /code

# Копируем только зависимости (чтобы использовать кэш)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Теперь копируем всё остальное
COPY . .

# Указываем команду запуска
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080"]

# пересобрать образ: docker build -t donatesite .
