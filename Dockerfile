# Use official Python image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files & enable stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
# RUN useradd --create-home appuser
RUN useradd --create-home --uid 1000 appuser

# Copy project files
COPY app.py .
COPY config.py .
COPY src/ ./src/

RUN mkdir -p input output && chown -R appuser /app

USER 1000

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
