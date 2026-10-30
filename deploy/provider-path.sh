#!/bin/sh
# Renders the provider endpoint for nginx from PROVIDER_SECRET, at container
# start (the nginx image runs /docker-entrypoint.d/*.sh before starting nginx).
#
#   PROVIDER_SECRET empty/unset -> open relay: provider at /api/v1/provider
#   PROVIDER_SECRET set         -> provider only at /<secret>/api/v1/provider,
#                                  and the bare /api/v1/provider returns 404.
#
# Clients are unaffected either way; only the provider URL changes.
set -eu

out=/etc/nginx/conf.d/provider.conf
secret="${PROVIDER_SECRET:-}"

if [ -n "$secret" ]; then
    # Keep it to URL-safe characters so it can't break the nginx config.
    case "$secret" in
        *[!A-Za-z0-9_-]*)
            echo "provider-path: ERROR - PROVIDER_SECRET may contain only letters, digits, '-' and '_' (no slashes or spaces). Fix .env and run 'docker compose up -d'." >&2
            exit 1
            ;;
    esac
    cat > "$out" <<EOF
# Generated from PROVIDER_SECRET: a provider can register only at the secret path.
location = /$secret/api/v1/provider {
    rewrite ^ /api/v1/provider break;
    proxy_pass \$relay;
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;
}
# The bare path is closed so the relay can't be found by guessing it.
location = /api/v1/provider { return 404; }
EOF
    echo "provider-path: locked (provider at /<secret>/api/v1/provider)"
else
    cat > "$out" <<EOF
# Generated from PROVIDER_SECRET (unset): open relay.
location = /api/v1/provider {
    proxy_pass \$relay;
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;
}
EOF
    echo "provider-path: open (provider at /api/v1/provider)"
fi
