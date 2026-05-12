# Imagen base
FROM python:3.12-slim

# Install Chromium and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Directory of the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

RUN chromium --version && chromedriver --version

# Run the application
CMD ["python", "index.py"]