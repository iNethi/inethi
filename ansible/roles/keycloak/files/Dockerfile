FROM quay.io/keycloak/keycloak:25.0.6 as builder

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

# Configure a database vendor
ENV KC_DB=postgres

# set working directory
WORKDIR /opt/keycloak