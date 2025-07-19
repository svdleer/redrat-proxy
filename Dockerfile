FROM python:3.9-slim

# Install required dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc python3-dev libmariadb-dev-compat libmariadb-dev libjpeg-dev zlib1g-dev curl && \
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
ENV PYTHONPATH="/app"

EXPOSE 5000

# Verify installed packages for debugging
RUN . venv/bin/activate && pip list

# Add entrypoint script to the container
COPY docker-entrypoint-new.sh /app/
RUN chmod +x /app/docker-entrypoint-new.sh

# Default command runs the app directly
# The docker-compose.yml will override this to use the entrypoint script
CMD ["/app/venv/bin/python", "app.py"]