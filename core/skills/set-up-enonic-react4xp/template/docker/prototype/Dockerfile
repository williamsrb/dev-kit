FROM node:{NODE_XP_VERSION}-alpine AS build-deps

WORKDIR /appwork

COPY prototype/ .

RUN corepack enable && yarn install && yarn run buildNext

FROM node:{NODE_XP_VERSION}-alpine AS production

WORKDIR /appwork

COPY prototype/ .
COPY --from=build-deps /appwork/.next ./.next
COPY --from=build-deps /appwork/public ./public
COPY --from=build-deps /appwork/node_modules ./node_modules

EXPOSE 80

ENV PORT=80

CMD ["yarn", "start"]
