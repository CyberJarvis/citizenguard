# CoastGuardian Backend - Production Dockerfile
# Optimized for Railway deployment with ML models

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=300

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV, ML, and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    libsndfile1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and install wheel for faster builds
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with better error handling
# Install in two stages: core deps first, then ML deps
RUN echo "=== Installing Core Dependencies ===" && \
    pip install --no-cache-dir \
    fastapi==0.109.2 \
    uvicorn[standard]==0.27.1 \
    python-multipart==0.0.9 \
    motor==3.3.2 \
    redis==5.0.1 \
    pymongo==4.6.1 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    bcrypt==4.0.1 \
    python-dotenv==1.0.1 \
    cryptography==42.0.0 \
    authlib==1.3.0 \
    httpx==0.26.0 \
    aiosmtplib==5.0.0 \
    email-validator==2.1.0 \
    jinja2==3.1.3 \
    twilio==8.12.0 \
    pydantic==2.6.4 \
    pydantic-settings==2.2.1 \
    python-dateutil==2.8.2 \
    pytz==2024.1 \
    pandas==2.0.3 \
    openpyxl==3.1.2 \
    reportlab==4.0.7 \
    apscheduler==3.10.4 \
    boto3==1.34.20 \
    aiohttp==3.9.1 \
    beautifulsoup4==4.12.2 \
    pywebpush==1.14.0 && \
    echo "=== Core Dependencies Installed ===" && \
    echo "=== Installing ML Dependencies ===" && \
    pip install --no-cache-dir \
    "numpy<2.0" \
    scikit-learn==1.3.2 \
    joblib==1.3.2 \
    Pillow==10.3.0 \
    opencv-python-headless==4.9.0.80 && \
    echo "=== Installing PyTorch (CPU) ===" && \
    pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.0.0+cpu \
    torchaudio==2.0.0+cpu && \
    echo "=== PyTorch Installed ===" && \
    echo "=== Installing Whisper & Transformers ===" && \
    pip install --no-cache-dir \
    openai-whisper==20231117 \
    faiss-cpu==1.7.4 \
    sentence-transformers==2.7.0 && \
    echo "=== All Dependencies Installed ==="

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p uploads data/models

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Health check - Railway will use this endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# Start command using startup script
CMD ["./start.sh"]
