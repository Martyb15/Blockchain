# Using a small-ish Python image
From python:3.12-slim

# Don't push buffer logs
ENV PYTHONUNBUFFERED=1

#Workdir inside the container
WORKDIR /app

# Copy what is needed for dependency install + imports
COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests

# Install project + dev deps
RUN python -m pip install -U pip \ 
    && pip install ".[dev]"

# Expose FastAPI port
EXPOSE 5000

# Start the API
CMD ["uvicorn", "pychain.api:app", "--host", "0.0.0.0", "--port", "5000"]
