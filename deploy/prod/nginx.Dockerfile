FROM node:20.5.0-alpine as builder

RUN npm install -g npm@latest

WORKDIR /app/kaimon/
COPY ./static/kaimon/ ./

RUN npm i --save --legacy-peer-deps

RUN npm run build

FROM nginx

COPY --from=builder /app/kaimon/build/ /usr/share/nginx/html

RUN rm /etc/nginx/conf.d/default.conf
COPY /deploy/prod/nginx.conf /etc/nginx/conf.d
