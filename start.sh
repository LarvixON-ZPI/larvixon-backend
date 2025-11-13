#!/bin/sh

echo "--- DIAGNOSTIC: Checking Environment Variables ---"
echo "FORCE_HTTPS = [$FORCE_HTTPS]"
echo "DEBUG = [$DEBUG]"
if [ -n "$PRE_BUILD_COMMAND" ]; then
    echo "PRE_BUILD_COMMAND is SET"
else
    echo "PRE_BUILD_COMMAND is NOT SET"
fi

if [ -n "$CELERY_BROKER_URL" ]; then
    echo "CELERY_BROKER_URL is SET (hidden)"
else
    echo "CELERY_BROKER_URL is NOT SET"
fi

if [ -n "$CELERY_RESULT_BACKEND" ]; then
    echo "CELERY_RESULT_BACKEND is SET (hidden)"
else
    echo "CELERY_RESULT_BACKEND is NOT SET"
fi
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