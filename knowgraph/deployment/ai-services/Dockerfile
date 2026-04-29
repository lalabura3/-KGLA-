FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy service files
COPY whisper_service.py .
COPY llm_service.py .

EXPOSE 8001 8002

# Start both services
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
