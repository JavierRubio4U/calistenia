#!/bin/bash
# Genera .streamlit/secrets.toml desde variables de entorno (Cloud Run)
mkdir -p /app/.streamlit
cat > /app/.streamlit/secrets.toml <<EOF
GEMINI_API_KEY = "${GEMINI_API_KEY}"
SUPABASE_URL = "${SUPABASE_URL}"
SUPABASE_KEY = "${SUPABASE_KEY}"
ALLOWED_EMAIL = "${ALLOWED_EMAIL}"

[auth]
redirect_uri = "${OAUTH_REDIRECT_URI}"
cookie_secret = "${COOKIE_SECRET}"

[auth.google]
client_id = "${GOOGLE_CLIENT_ID}"
client_secret = "${GOOGLE_CLIENT_SECRET}"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF

exec streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0
