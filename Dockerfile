# Use the official Python image from the Docker Hub with Python 3.11.7
FROM python:3.11.7-slim AS build

# Set environment variables
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the application code into the container
COPY . /app

EXPOSE 8080

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "main.py"]

# CMD ["gunicorn", "main:app"]