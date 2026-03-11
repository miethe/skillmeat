# syntax=docker/dockerfile:1

# ---- Stage 1: Install dependencies ----
FROM node:20-slim AS deps

RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile --prod=false

# ---- Stage 2: Build the application ----
FROM node:20-slim AS builder

RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Internal API URL for Next.js rewrites (baked into standalone build at compile time).
# Override at build time: docker build --build-arg INTERNAL_API_URL=http://my-api:8080
ARG INTERNAL_API_URL=http://skillmeat-api:8080
ENV INTERNAL_API_URL=$INTERNAL_API_URL

# Raise open-file limit for Next.js build (Podman defaults are often too low)
RUN ulimit -n 65536 2>/dev/null || true; pnpm build

# ---- Stage 3: Production runner ----
FROM node:20-slim AS runner

LABEL org.opencontainers.image.source="https://github.com/miethe/skillmeat"
LABEL org.opencontainers.image.description="SkillMeat Web Interface - Collection browser and management dashboard"

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 --ingroup nodejs nextjs

# Copy standalone server output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./

# Copy static assets (not included in standalone output)
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy public assets
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "const http = require('http'); const req = http.get('http://localhost:3000/', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); }); req.on('error', () => process.exit(1)); req.setTimeout(3000, () => { req.destroy(); process.exit(1); });"

CMD ["node", "server.js"]
