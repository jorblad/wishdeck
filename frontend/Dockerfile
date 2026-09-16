# frontend/Dockerfile
# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install -g @quasar/cli && npm install
COPY . .
RUN quasar build

# ---- Dev stage (keeps Node + quasar CLI for hot reload) ----
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json ./
RUN npm install -g @quasar/cli && npm install
COPY . .
EXPOSE 9000
CMD ["sh", "-c", "npm install && quasar dev --host 0.0.0.0 --port 9000"]

# ---- Runtime (production) stage ----
FROM nginx:1.31-alpine AS runtime
COPY --from=build /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
