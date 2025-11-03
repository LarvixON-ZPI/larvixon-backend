# ZMIANA 1: Użyj tej samej wersji Pythona co lokalnie (3.10)
FROM python:3.10-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Twoja lista zależności systemowych jest świetna, rozwiązuje błąd OpenCV
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
# Dodano --no-cache-dir, aby obraz był mniejszy
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

# Ta linia nie jest już potrzebna, `collectstatic` użyje STATIC_ROOT
# RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

# ZMIANA 2: Dodaj `collectstatic` na początek polecenia startowego.
# To jest absolutnie krytyczne dla plików CSS/JS.
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000"]
