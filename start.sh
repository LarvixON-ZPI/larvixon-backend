#!/bin/sh

echo "--- DIAGNOSTIC: Checking Environment Variables ---"
echo "FORCE_HTTPS = [$FORCE_HTTPS]"
echo "DEBUG = [$DEBUG]"
echo "PRE_BUILD_COMMAND (first 30 chars) = [${PRE_BUILD_COMMAND:0:30}...]"
echo "CELERY_BROKER_URL (first 30 chars) = [${CELERY_BROKER_URL:0:30}...]"
echo "CELERY_RESULT_BACKEND (first 30 chars) = [${CELERY_RESULT_BACKEND:0:30}...]"
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
exec gunicorn larvixon_site.wsgi:application --bind 0.0.0.0:8000 --workers 4 --forwarded-allow-ips="*"