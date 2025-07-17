FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy application code
COPY sx_locust/ ./sx_locust/

# Expose port
EXPOSE 8089

# Run locust
CMD ["python", "-m", "locust", "--locustfile=sx_locust/locustfile.py", "--master", "--web-host=0.0.0.0", "--web-port=8089"]