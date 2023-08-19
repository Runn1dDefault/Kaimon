FROM nginx

COPY /deploy/dev/nginx.conf /etc/nginx/conf.d/default.conf
