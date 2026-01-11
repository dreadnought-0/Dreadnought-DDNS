FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Create appuser with specific UID/GID
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create /data directory with proper ownership
RUN mkdir -p /data && chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]