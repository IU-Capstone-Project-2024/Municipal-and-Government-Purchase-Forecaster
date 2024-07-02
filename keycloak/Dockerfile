FROM quay.io/keycloak/keycloak:latest
ENV KEYCLOAK_ADMIN=admin
ENV KEYCLOAK_ADMIN_PASSWORD=pass12345
ENV DB_VENDOR=postgres
ENV DB_ADDR=postgres
ENV DB_DATABASE=keycloak
ENV DB_USER=keycloak
ENV DB_PASSWORD=postgrepass12345
ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start-dev"]
