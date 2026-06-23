FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /workspace/CAI

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libglib2.0-0 \
    libgl1 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY docs/requirements.txt /tmp/CAI-requirements.txt

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install torch torchvision --index-url ${TORCH_INDEX_URL} && \
    python -m pip install -r /tmp/CAI-requirements.txt

COPY . .

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "dashboard/comprehensive_dashboard.py", "--server.address=0.0.0.0", "--server.port=8501"]
