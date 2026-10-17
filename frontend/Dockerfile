FROM node:24-alpine AS base
WORKDIR /app

FROM base AS deps
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
ARG VITE_API_URL=http://backend:8000
ARG VITE_API_KEY=dev-key
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_KEY=$VITE_API_KEY
RUN npm run build

FROM base AS runtime
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
USER appuser
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:5173/ || exit 1
CMD ["npx", "vite", "preview", "--host", "127.0.0.1", "--port", "5173"]