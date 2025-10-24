FROM python:3.13.7-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
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
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000

# Run migrations
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000"]
