#!/bin/sh

echo "--- Running migrations ---"
python manage.py migrate --noinput

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput

echo "--- Starting supervisord ---"
exec /usr/bin/supervisord