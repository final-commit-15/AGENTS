FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (if any)
# RUN apt-get update && apt-get install -y ...

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use a non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Command: run the agent service (e.g., a FastAPI app or a worker)
# For simplicity, we'll run a script that loads agents and keeps alive
CMD ["python", "-m", "app.main"]