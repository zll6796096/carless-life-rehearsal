#!/bin/sh
set -e

PORT="${PORT:-8080}"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

# Generate runtime config.js
cat <<EOF > /usr/share/nginx/html/config.js
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF

# Substitute PORT into nginx configuration
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Execute nginx in foreground
exec nginx -g 'daemon off;'
