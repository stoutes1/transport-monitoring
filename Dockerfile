FROM python:3.9-slim

WORKDIR /app

# Устанавливаем зависимости в правильном порядке
RUN pip install --no-cache-dir numpy==1.21.6 pandas==1.3.5

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

# Используем прямое указание на app.py
CMD ["python", "app.py"]