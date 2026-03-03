# ---- build ----
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime ----
FROM nginx:alpine

# Copia build do frontend
COPY --from=build /app/dist /usr/share/nginx/html

# Copia template nginx (envsubst resolve $BACKEND_URL automaticamente)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
