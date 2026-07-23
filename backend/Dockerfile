FROM python:3.11-slim

# WeasyPrintとOpenCV、ffmpegに必要なシステムライブラリをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    gobject-introspection \
    libglib2.0-dev \
    libgl1 \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# メディアデータを保存するディレクトリを作成
RUN mkdir -p /app/media/videos /app/media/images /app/media/pdfs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
