FROM nginx:1.25-alpine

# Remove default configuration files
RUN rm /etc/nginx/nginx.conf
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configurations
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Expose ports
EXPOSE 80 443

# Command to run Nginx
CMD ["nginx", "-g", "daemon off;"]
