#!/bin/bash

# Generate a self-signed SSL certificate with OpenSSL


# Check if OpenSSL is installed
if ! [ -x "$(command -v openssl)" ]; then
  echo 'Error: OpenSSL is not installed.' >&2
  exit 1
fi

# Generate a Private Key
openssl genrsa -out /etc/nginx/certs/private_gateway.pem 2048

# Generate a CSR (Certificate Signing Request)
openssl req -new -key /etc/nginx/certs/private_gateway.pem -out /etc/nginx/certs/server_gateway.csr -subj "/C=PT/ST=Aveiro/L=Earth/O=IT/OU=IT/CN=www.gsma-open-gateway.com/emailAddress=email@example.com"

# Generate a Self Signed Certificate
openssl x509 -req -days 365 -in /etc/nginx/certs/server_gateway.csr -signkey /etc/nginx/certs/private_gateway.pem -out /etc/nginx/certs/self_signed_gateway.pem
