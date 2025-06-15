FROM python:3.10-slim

# Install system dependencies for geospatial Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libgeos-dev \
    libproj-dev \
    proj-data \
    libgeotiff-dev \
    libspatialite-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .
COPY bike_rent.py .
COPY functions.py .

# Run your main script
CMD ["python", "bike_rent.py"]
