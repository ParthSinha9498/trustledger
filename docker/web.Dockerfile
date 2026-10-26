FROM node:22-alpine AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY web .
# NEXT_PUBLIC_* values are inlined into the browser bundle at build time.
#   Local / compose:  NEXT_PUBLIC_API_URL (default http://localhost:8000)
#   Render:           API_PUBLIC_HOST = the api service's onrender.com hostname (from render.yaml);
#                     used only when NEXT_PUBLIC_API_URL is empty.
# Render passes every env var of the service as a build arg, so only public values belong here.
ARG NEXT_PUBLIC_API_URL=""
ARG API_PUBLIC_HOST=""
ARG NEXT_PUBLIC_AG_GRID_LICENSE=""
ARG NEXT_PUBLIC_PAYPAL_CLIENT_ID=""
ENV NEXT_PUBLIC_AG_GRID_LICENSE=$NEXT_PUBLIC_AG_GRID_LICENSE \
    NEXT_PUBLIC_PAYPAL_CLIENT_ID=$NEXT_PUBLIC_PAYPAL_CLIENT_ID \
    NEXT_TELEMETRY_DISABLED=1
RUN if [ -z "$NEXT_PUBLIC_API_URL" ]; then \
      if [ -n "$API_PUBLIC_HOST" ]; then NEXT_PUBLIC_API_URL="https://$API_PUBLIC_HOST"; \
      else NEXT_PUBLIC_API_URL="http://localhost:8000"; fi; \
    fi; \
    echo "Building with NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL"; \
    NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
# Render sets PORT (10000 by default); server.js reads PORT and HOSTNAME.
CMD ["node", "server.js"]
