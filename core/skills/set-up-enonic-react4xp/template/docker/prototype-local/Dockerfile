FROM node:{NODE_XP_VERSION}-alpine

WORKDIR /usr/app/prototype

# Copy only dependency files first (build cache)
COPY prototype/package.json prototype/package-lock.json ./

RUN npm ci

COPY prototype .

EXPOSE 3000

CMD ["npm", "run", "dev"]
