FROM python:3.9
USER root

# 作業ディレクトリを作成
WORKDIR /app

# requirements.txtをコンテナにコピー
COPY requirements.txt .

# requirements.txtに記載されたライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5050
CMD ["python", "app.py"]