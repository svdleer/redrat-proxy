FROM python:3.9-slim

# Install required dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc python3-dev libmariadb-dev-compat libmariadb-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

WORKDIR /app

# Setup virtual environment
RUN pip install --no-cache-dir virtualenv && \
    python -m venv venv

# Activate virtual environment and install dependencies
COPY requirements.txt .
RUN . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Ensure proper directories exist with permissions
RUN mkdir -p /app/app/static/remote_images && \
    chmod -R 777 /app/app/static

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH="/app:${PYTHONPATH}"

EXPOSE 5000

# Verify installed packages for debugging
RUN . venv/bin/activate && pip list

# Add entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]

# Use the virtual environment's Python and Gunicorn
CMD ["./venv/bin/gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--log-level", "debug", "--chdir", "/app", "app:app"]