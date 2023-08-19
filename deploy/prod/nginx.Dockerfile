FROM nginx

RUN rm /etc/nginx/conf.d/default.conf

COPY /deploy/prod/nginx.conf /etc/nginx/conf.d
