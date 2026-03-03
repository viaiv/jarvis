# ---- build ----
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime ----
FROM nginx:alpine

ENV BACKEND_URL=http://backend:8000

# Copia build do frontend
COPY --from=build /app/dist /usr/share/nginx/html

# Copia template nginx (envsubst resolve apenas $BACKEND_URL, preservando vars do nginx)
COPY nginx.conf.template /etc/nginx/nginx.conf.template

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '$BACKEND_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
