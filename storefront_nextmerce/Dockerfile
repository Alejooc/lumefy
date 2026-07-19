FROM node:24-alpine AS build

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_PLATFORM_STOREFRONT_DOMAIN
ENV NEXT_PUBLIC_PLATFORM_STOREFRONT_DOMAIN=$NEXT_PUBLIC_PLATFORM_STOREFRONT_DOMAIN

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:24-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV INTERNAL_API_URL=http://backend:8000/api/v1

COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
