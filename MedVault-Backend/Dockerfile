FROM node:18-alpine

WORKDIR /app

# Copy package descriptors and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Expose port from server.js
EXPOSE 5000

# Start backend server
CMD ["npm", "start"]
