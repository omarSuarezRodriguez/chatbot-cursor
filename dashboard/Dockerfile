FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py shell -c \"from django.contrib.auth import get_user_model;U=get_user_model();u,_=U.objects.get_or_create(username='admin',defaults={'is_staff':True,'is_superuser':True,'email':'admin@example.com'});u.is_staff=True;u.is_superuser=True;u.set_password('1234');u.save();print('admin-ready')\" && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]
