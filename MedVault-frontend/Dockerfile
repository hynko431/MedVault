FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (use legacy-peer-deps to avoid upstream conflicts if any)
RUN npm install

# Copy the rest of the application
COPY . .

# Expose Metro bundler port
EXPOSE 8081

# Command to run the Expo development server
CMD ["npm", "start"]
