FROM nginxinc/nginx-unprivileged:1.29.2-alpine3.22-slim
COPY nginx.conf /etc/nginx/nginx.conf
COPY certs /etc/nginx/certs
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]