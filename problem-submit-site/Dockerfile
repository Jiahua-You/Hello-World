FROM python:3.10-slim

WORKDIR /app

# Install PostgreSQL client dependencies
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY index.html server.py ./

# Default port
ENV PORT=8000
EXPOSE 8000

# Command to run the application
CMD ["python", "server.py"]
