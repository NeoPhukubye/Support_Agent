FROM node:20-slim

WORKDIR /app

# Install deps first (cached layer)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

EXPOSE 5173

# Vite must bind to 0.0.0.0 to be reachable from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
