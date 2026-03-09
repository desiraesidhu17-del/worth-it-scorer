FROM python:3.11-slim

# Install system dependencies for Playwright + lxml
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium + its OS dependencies
RUN playwright install chromium --with-deps

# Copy app
COPY . .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8080
ENV PORT=8080

CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
