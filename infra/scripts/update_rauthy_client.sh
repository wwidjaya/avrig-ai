#!/bin/bash
set -e
systemctl stop rauthy

# Backup database before modification
cp /var/lib/rauthy/data/state_machine/db/hiqlite.db /var/lib/rauthy/data/state_machine/db/hiqlite.db.bak-$(date +%s)

sqlite3 /var/lib/rauthy/data/state_machine/db/hiqlite.db "
UPDATE clients SET 
    redirect_uris = 'https://app.avrig.ai/auth/callback,https://avrig.ai/auth/callback,https://web.avrig.ai/auth/callback,http://localhost:3000/auth/callback',
    post_logout_redirect_uris = 'https://app.avrig.ai/logged-out,https://app.avrig.ai/,https://app.avrig.ai,https://avrig.ai/,https://web.avrig.ai/,https://avrig.ai,https://web.avrig.ai,http://localhost:3000/,http://localhost:3000',
    allowed_origins = 'https://app.avrig.ai,https://avrig.ai,https://web.avrig.ai,http://localhost:3000'
WHERE id = 'avrig-web-ui';

INSERT OR REPLACE INTO clients (
    id, name, enabled, confidential, secret, secret_kid,
    redirect_uris, post_logout_redirect_uris, allowed_origins,
    flows_enabled, access_token_alg, id_token_alg,
    auth_code_lifetime, access_token_lifetime, scopes, default_scopes,
    challenge, force_mfa, client_uri, contacts,
    backchannel_logout_uri, restrict_group_prefix, claims, claims_at_root,
    allowed_resources, default_aud
)
SELECT 
    'avrig-app', name, enabled, confidential, secret, secret_kid,
    'https://app.avrig.ai/auth/callback,https://avrig.ai/auth/callback,https://web.avrig.ai/auth/callback,http://localhost:3000/auth/callback',
    'https://app.avrig.ai/logged-out,https://app.avrig.ai/,https://app.avrig.ai,https://avrig.ai/,https://web.avrig.ai/,https://avrig.ai,https://web.avrig.ai,http://localhost:3000/,http://localhost:3000',
    'https://app.avrig.ai,https://avrig.ai,https://web.avrig.ai,http://localhost:3000',
    flows_enabled, access_token_alg, id_token_alg,
    auth_code_lifetime, access_token_lifetime, scopes, default_scopes,
    challenge, force_mfa, client_uri, contacts,
    backchannel_logout_uri, restrict_group_prefix, claims, claims_at_root,
    allowed_resources, default_aud
FROM clients WHERE id = 'avrig-web-ui';

PRAGMA wal_checkpoint(TRUNCATE);
"
systemctl start rauthy
sleep 3
systemctl status rauthy --no-pager
