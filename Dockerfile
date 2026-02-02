# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for some python packages)
# Rocky 9 equivalent would be typically dnf, but inside python-slim (Debian based) it's apt-get.
# If we wanted a Rocky-based container we'd use rockylinux:9 but python:3.9-slim is standard and smaller.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Initialize the database (this runs once during build, but better to run at startup if volume is mounted)
# We will handle db init in the code (main.py calls init_db)

# Command to run on container start
CMD ["python", "main.py"]
