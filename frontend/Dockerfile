# frontend/Dockerfile
# @quasar/app-vite v3 requires Node >= 22.22
# ---- Build stage ----
FROM node:24-alpine AS build
# Quasar picks the package manager from the installed binaries when no lockfile
# exists (we install with --no-package-lock). Force npm: yarn v1 mis-resolves
# rollup's libc-specific native binaries on Alpine (musl) and aborts the PWA
# build, whereas npm correctly skips libc-incompatible optional dependencies.
RUN rm -f "$(command -v yarn 2>/dev/null)" "$(command -v yarnpkg 2>/dev/null)" 2>/dev/null; corepack disable 2>/dev/null || true
WORKDIR /app
COPY package.json ./
RUN npm install -g @quasar/cli && npm install --legacy-peer-deps --no-package-lock
COPY . .
RUN quasar build -m pwa

# ---- Dev stage (keeps Node + quasar CLI for hot reload) ----
FROM node:24-alpine AS dev
RUN rm -f "$(command -v yarn 2>/dev/null)" "$(command -v yarnpkg 2>/dev/null)" 2>/dev/null; corepack disable 2>/dev/null || true
WORKDIR /app
COPY package.json ./
RUN npm install -g @quasar/cli && npm install --legacy-peer-deps --no-package-lock
COPY . .
EXPOSE 9000
CMD ["sh", "-c", "npm install --legacy-peer-deps --no-package-lock && quasar dev --hostname 0.0.0.0 --port 9000"]

# ---- Runtime (production) stage ----
FROM nginx:1.31-alpine AS runtime
COPY --from=build /app/dist/pwa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
