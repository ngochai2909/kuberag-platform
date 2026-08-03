# syntax=docker/dockerfile:1.7
ARG NODE_IMAGE=cgr.dev/chainguard/node@sha256:576199e9510d2c40c75374ed80c15b3113a479d19ac061d998c3318adbaf75d8
ARG NGINX_IMAGE=cgr.dev/chainguard/nginx@sha256:e4ff957080737c90a9ecfeaa40e3d19ea9d687e9cacda2f2a031c75ffcdd72b7

FROM ${NODE_IMAGE} AS builder
WORKDIR /app

COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci
COPY apps/frontend ./

ARG VITE_API_MODE=real
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_MODE=${VITE_API_MODE} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM ${NGINX_IMAGE} AS runtime
COPY --from=builder --chown=65532:65532 /app/dist /usr/share/nginx/html
COPY --chown=65532:65532 apps/frontend/nginx.conf /etc/nginx/nginx.conf

USER 65532
EXPOSE 8080
