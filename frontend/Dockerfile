FROM node:22-alpine

WORKDIR /app

# package.json と package-lock.json をコピー
COPY package*.json ./

RUN npm install

# ソースコードをコピー
COPY . .

EXPOSE 4200

# 開発用サーバーを外部接続許可して起動 (ホストチェック無効化)
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--disable-host-check"]
