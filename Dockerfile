FROM python:3.11-slim

WORKDIR /home/ikisugikun

# 最小限のパッケージを入れてキャッシュを削除
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 依存は requirements.txt に分離（ビルドキャッシュ活用 & --no-cache-dir でイメージ軽量化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションをコピー
COPY src/ .

CMD ["python", "client.py"]