FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc python3-dev libmariadb-dev-compat libmariadb-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static/remote_images && \
    chmod -R 777 /app/static

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]