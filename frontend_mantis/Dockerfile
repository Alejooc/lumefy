# Stage 1: Build the Angular application
FROM node:20-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application for production
# Override base-href /angular/free/ to / for root deployment in Docker
RUN npm run build-prod -- --base-href /

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output to replace the default nginx contents.
# angular.json "outputPath": "dist" implies direct output to dist folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
