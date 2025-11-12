#!/bin/sh

echo "--- Running database migrations ---"
python manage.py migrate --noinput

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput

echo "--- Starting Celery worker in background... ---"
celery -A larvixon_site worker -l info &

echo "--- Starting Celery Beat (scheduler) in background... ---"
celery -A larvixon_site beat -l info &

echo "--- Starting Gunicorn (main process)... ---"
exec gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000 --workers 4 --forwarded-allow-ips="*"