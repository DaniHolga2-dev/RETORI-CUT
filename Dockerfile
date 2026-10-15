
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

WORKDIR /app

# Instalar FFmpeg y sus dependencias
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Preparar archivos estáticos y migraciones
RUN python manage.py collectstatic --noinput

EXPOSE 10000

# Arrancar Django con Gunicorn
CMD ["sh", "-c", "python manage.py migrate && exec gunicorn editor.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120"]
