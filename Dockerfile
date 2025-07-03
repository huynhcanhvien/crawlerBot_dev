# Use Python base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    # Additional dependencies for various packages
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# Note: This includes BERTopic, sentence-transformers, and other ML packages
# Set BLIS_ARCH to generic to avoid compilation issues on different architectures
ENV BLIS_ARCH=generic

# Upgrade pip, setuptools, and wheel to latest versions
RUN pip install --upgrade pip setuptools wheel

# Install problematic packages first with pre-built wheels
RUN pip install --no-cache-dir \
    --prefer-binary \
    numpy \
    scipy \
    blis \
    spacy

# Install remaining requirements with PEP 517
RUN pip install --no-cache-dir --use-pep517 -r requirements.txt

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('wordnet'); nltk.download('stopwords'); nltk.download('omw-1.4')"

# Create necessary directories
RUN mkdir -p /app/logs

# Copy application code
COPY . .

# Set permissions for logs directory
RUN chmod -R 755 /app/logs

# Expose port
EXPOSE 5003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5003/health || exit 1

# Run the application
CMD ["python", "-m", "app.api"]