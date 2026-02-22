# ============================================================
# Whydud Frontend — Multi-stage Dockerfile
# Base: Node 22-alpine
# ============================================================

ARG NODE_VERSION=22
FROM node:${NODE_VERSION}-alpine AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
FROM base AS deps

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
FROM base AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

# Build-time env vars (non-secret)
ARG NEXT_PUBLIC_API_URL=https://whydud.com
ARG NEXT_PUBLIC_SITE_URL=https://whydud.com

RUN npm run build

# ---------------------------------------------------------------------------
# Production runner
# ---------------------------------------------------------------------------
FROM base AS production

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
