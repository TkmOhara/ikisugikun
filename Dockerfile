FROM ubuntu:latest

WORKDIR /home/ikisugikun

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-pip

RUN pip install discord.py python-dotenv PyNaCl --break-system-packages

COPY src/ .

CMD ["python3", "client.py"]