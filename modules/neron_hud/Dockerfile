FROM node:20-slim AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npx tsx script/build.ts

FROM node:20-slim AS runner

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY --from=builder /app/dist ./dist

ENV NODE_ENV=production
ENV PORT=8080
ENV NERON_CORE_URL=http://neron_core:8000
ENV NERON_STT_URL=http://neron_stt:8001
ENV NERON_WATCHDOG_URL=http://neron_watchdog:8003

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8080/api/chat/history',r=>process.exit(r.statusCode<400?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "dist/index.cjs"]
