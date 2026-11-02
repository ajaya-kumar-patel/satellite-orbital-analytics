FROM python:3.13-slim

WORKDIR /app

# Install project dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project source and pipeline scripts
COPY src/ src/
COPY scripts/ scripts/
COPY tests/ tests/

# Default command: show pipeline usage
CMD ["bash", "scripts/run_pipeline.sh", "--help"]
