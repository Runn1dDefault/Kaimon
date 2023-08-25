#!/bin/bash

echo "Waiting for postgres..."
  while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.1
  done
echo "Postgres started"


pip install --upgrade pip

echo 'Start making migrations...'
python manage.py makemigrations --no-input
python manage.py migrate --no-input

echo 'Collecting static files...'
python manage.py collectstatic --no-input

echo 'Running server...'
gunicorn kaimon.wsgi:application --bind 0.0.0.0:8334
