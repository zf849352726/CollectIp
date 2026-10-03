FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY ip_operator ip_operator
COPY proxy_web proxy_web
COPY webapp webapp
COPY manage.py ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python manage.py collectstatic --noinput

ENV COLLECTIP_DEBUG=false
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "webapp.wsgi:application"]
