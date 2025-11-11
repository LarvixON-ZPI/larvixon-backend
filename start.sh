#!/bin/sh

echo "--- Installing system packages... ---"
apt-get update
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

echo "--- Running database migrations ---"
python manage.py migrate --noinput

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput

echo "--- Starting Celery worker in background... ---"
celery -A larvixon_site worker -l info &

echo "--- Starting Gunicorn (main process)... ---"
exec gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000 --workers 4