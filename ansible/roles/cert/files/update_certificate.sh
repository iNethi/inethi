#!/bin/bash

# Load environment variables from .env
set -a
source ./.env
set +a

# Define variables
KEYSTORE_PASS="iNethi2023#"
CERT_URL="http://54.88.150.74/cert/acme.json"
CERT_FILE="/mnt/data/traefik/letsencrypt/acme.json"
KEYCLOAK_CERT_DIR="/mnt/data/keycloak/certs"


# Download the current certificate
curl -L -k "https://54.88.150.74/cert/acme.json" -o "/mnt/data/traefik/letsencrypt/acme.json.new"

# Check if the certificate has changed
if ! cmp -s "${CERT_FILE}" "${CERT_FILE}.new"; then
    echo "Certificate has changed. Updating..."

    # Replace the old certificate
    mv "${CERT_FILE}.new" "${CERT_FILE}"
    chmod 600 ${CERT_FILE}

    # Extract certificate and key
    jq -r '.letsencrypt.Certificates[] | select(.domain.main == "inethilocal.net") | .certificate' "${CERT_FILE}" | base64 -d > "${KEYCLOAK_CERT_DIR}/cert.pem"
    jq -r '.letsencrypt.Certificates[] | select(.domain.main == "inethilocal.net") | .key' "${CERT_FILE}" | base64 -d > "${KEYCLOAK_CERT_DIR}/privkey.pem"

    # Generate keystore for Keycloak
    openssl pkcs12 -export -in "${KEYCLOAK_CERT_DIR}/cert.pem" -inkey "${KEYCLOAK_CERT_DIR}/privkey.pem" -out "${KEYCLOAK_CERT_DIR}/keystore.p12" -name keycloak -password pass:"${KEYSTORE_PASS}"
    keytool -importkeystore -deststorepass "${KEYSTORE_PASS}" -destkeypass "${KEYSTORE_PASS}" -destkeystore "${KEYCLOAK_CERT_DIR}/keystore.jks" -srckeystore "${KEYCLOAK_CERT_DIR}/keystore.p12" -srcstoretype PKCS12 -alias keycloak -srcstorepass "${KEYSTORE_PASS}" -noprompt

    # Restart Traefik container
    if docker ps -a -q -f name=inethi-traefikssl; then
        docker restart inethi-traefikssl
        echo "Restarted traefik container."
    fi

    # Restart Keycloak container
    if docker ps -a -q -f name=inethi-keycloak; then
        docker restart inethi-keycloak
        echo "Restarted Keycloak container."
    fi
else
    echo "Certificate has not changed. No action required."
    rm -f "${CERT_FILE}.new"
fi

