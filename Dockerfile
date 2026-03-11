FROM python:3.11-slim

# Ensure Python output is sent straight to Docker logs
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]
