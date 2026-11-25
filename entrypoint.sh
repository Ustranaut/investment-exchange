#!/bin/sh
set -e

# Учебный bootstrap: создаёт начальные миграции при первом запуске.
# После первого запуска добавьте созданные apps/*/migrations/*.py в GitHub.
if [ "${DJANGO_AUTO_MIGRATE:-1}" = "1" ]; then
    python manage.py makemigrations users packages orders promotions market audit
    python manage.py migrate --noinput
fi

python manage.py seed_demo

exec "$@"
