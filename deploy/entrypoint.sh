#!/bin/bash

pip install --upgrade pip

python manage.py makemigrations --no-input

python manage.py migrate --no-input

python manage.py collectstatic --no-input

gunicorn kaimon.wsgi:application --bind 0.0.0.0:8334
