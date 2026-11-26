FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PORT=8090 \
    HF_HOME=/tmp/hf_cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fontconfig fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY web ./web
COPY fonts ./fonts

RUN mkdir -p /usr/share/fonts/eu-edito && cp -r ./fonts/* /usr/share/fonts/eu-edito/ && fc-cache -fv

EXPOSE 8090
CMD ["python", "backend/server.py"]
