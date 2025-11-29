# Using a small-ish Python image
From python:3.12-slim

# Don't push buffer logs
ENV PYTHONUNBUFFERED=1

#Workdir inside the container
WORKDIR /app

# Install dependencies 
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . . 

# Expose FastAPI port
EXPOSE 5000

# Start the API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5000"]
