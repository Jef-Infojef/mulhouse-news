# Site mulhouse-actu servi depuis le VPS (Vercel ne fait plus que relayer :
# le Postgres du VPS n'accepte pas les IP de Vercel). Les scrapers du dépôt
# tournent dans GitHub Actions, pas dans cette image.
FROM node:22-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app
COPY package.json package-lock.json* ./
COPY prisma ./prisma
RUN npm install

FROM base AS builder
RUN apk add --no-cache openssl
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# .env.production (non versionné, déposé sur le VPS) est lu par next build
RUN npm run build

FROM base AS runner
RUN apk add --no-cache openssl
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3200
ENV HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/next.config.* ./

USER nextjs
EXPOSE 3200
CMD ["npx", "next", "start", "-p", "3200"]
