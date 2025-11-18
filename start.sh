#!/bin/sh

echo "--- Installing system packages (libgl1, postgresql-client)... ---"
apt-get update -y
apt-get install -y --no-install-recommends \
    postgresql-client \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1
echo "--- System packages installed. ---"

echo "--- Installing pip packages... ---"
pip install --upgrade pip
pip install -r requirements.txt
echo "--- Pip packages installed. ---"

echo "--- DIAGNOSTIC: Checking Environment Variables ---"
echo "FORCE_HTTPS = [$FORCE_HTTPS]"
if [ -n "$CELERY_BROKER_URL" ]; then echo "CELERY_BROKER_URL is SET (hidden)"; else echo "CELERY_BROKER_URL is NOT SET"; fi
if [ -n "$CELERY_RESULT_BACKEND" ]; then echo "CELERY_RESULT_BACKEND is SET (hidden)"; else echo "CELERY_RESULT_BACKEND is NOT SET"; fi
echo "--- END OF DIAGNOSTICS ---"

echo "--- Running database migrations ---"
python manage.py migrate --noinput

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput

echo "--- Starting Celery worker in background... ---"
celery -A larvixon_site worker -l info &

echo "--- Starting Celery Beat (scheduler) in background... ---"
celery -A larvixon_site beat -l info &

echo "--- Starting Gunicorn (main process)... ---"
exec gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120