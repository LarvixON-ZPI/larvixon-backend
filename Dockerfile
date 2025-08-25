FROM python:3.13.7-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app

EXPOSE 8000

# Run migrations (SQLite is file-based, no waiting needed)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000"]
