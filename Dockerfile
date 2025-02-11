FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml poetry.lock ./

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy the rest of the application
COPY . .

# Create a directory for the database
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app/src \
    DB_PATH=/app/data/sarah_testing.db

# Run the application
ENTRYPOINT ["streamlit", "run", "src/sarah_streamlit/testing_app.py", "--server.port=8080", "--server.address=0.0.0.0"] 