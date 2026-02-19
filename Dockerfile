# IXOM-POC Production Dockerfile
# Multi-stage build for optimized image size and security

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY core/ ./core/
COPY .streamlit/ ./.streamlit/
COPY assets/ ./assets/
COPY *.py ./
COPY data/mapping.xlsx ./data/mapping.xlsx

# Create necessary directories with proper permissions
RUN mkdir -p \
    data/specs \
    data/certificates \
    logs \
    outputs/structured_json \
    && chmod -R 755 /app

# Create non-root user for security (optional but recommended)
# RUN useradd -m -u 1000 ixomuser && chown -R ixomuser:ixomuser /app
# USER ixomuser

# Expose Streamlit default port
EXPOSE 8501

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Run Streamlit application
CMD ["streamlit", "run", "ui.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
