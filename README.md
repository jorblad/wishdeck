# wishdeck
Vibecoded wishlist system

## Settings

WishDeck is configured through environment variables. Backend settings are
read on startup; most can also be overridden at runtime from the **Settings**
page (stored in the database with environment variables as defaults).

### Backend

| Variable | Description | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Full DB connection string | With cnpg, mount the cluster secret and set this to `secretKeyRef name=<cluster> key=uri`. Bare `postgresql://` is rewritten to the async `psycopg` driver automatically. |
| `SECRET_KEY` | JWT signing key | **Required.** Use a long random value (e.g. `openssl rand -hex 32`). |
| `ALGORITHM` | JWT algorithm | Default `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session lifetime | Default `2880` (48h). |
| `CORS_ORIGINS` | Allowed CORS origins | Comma-separated. Empty in single-ingress deployments (same-origin cookie auth). |
| `BASE_URL` | Public base URL | Used to build default OIDC redirect URIs. |
| `ENABLE_REGISTRATION` | Allow local signup | `true`/`false`. First user is always admin. |
| `ALLOWED_EMAIL_DOMAINS` | Restrict local signup | Comma-separated domains; empty = open. |
| `OIDC_ENABLED` | Enable SSO login | `true`/`false`. |
| `OIDC_NAME` | Button label for the SSO button | e.g. `Microsoft` or `Entra ID`. |
| `OIDC_ISSUER_URL` | Provider Issuer (base URL) | e.g. `https://login.microsoftonline.com/<TENANT>/v2.0`. The discovery document is fetched from `<issuer>/.well-known/openid-configuration`. |
| `OIDC_CLIENT_ID` | OIDC client/application ID | Registered in your IdP. |
| `OIDC_CLIENT_SECRET` | OIDC client secret | Only needed for secret-based token exchange. |
| `OIDC_SCOPES` | Requested scopes | Default `openid email profile`. |
| `OIDC_REDIRECT_URI` | Explicit redirect URI | Usually left empty; defaults to `<BASE_URL>/api/v1/auth/oidc/callback`. |
| `OIDC_AUTO_CREATE_USERS` | JIT-provision IdP users | `true` (default) auto-creates accounts on first login. |
| `OIDC_DEFAULT_ROLE` | Role for new OIDC users | `user` (default) or `admin`. |

### Frontend (OIDC)

The frontend reads its OIDC configuration from `GET /api/v1/auth/oidc/config`
at startup, so the **backend** `OIDC_*` variables are the single source of
truth. The frontend:

- Builds the login redirect from the provider's **discovery document**
  (works with Entra ID, Keycloak, Google, etc. — no hardcoded paths).
- Uses `window.location.origin + /oidc/callback` as the `redirect_uri`.
  This must be registered as a **reply URL** in your IdP.
- Exchanges the returned `code` at `/api/v1/auth/oidc/callback` and stores the
  session cookie.

### Example: Microsoft Entra ID

1. Register an app in Entra ID (App registrations).
2. Add a **Web** platform redirect URI:
   `https://<your-domain>/oidc/callback`
3. Create a client secret.
4. Set backend env vars:

   ```
   OIDC_ENABLED=true
   OIDC_NAME=Microsoft
   OIDC_ISSUER_URL=https://login.microsoftonline.com/<TENANT-ID>/v2.0
   OIDC_CLIENT_ID=<APPLICATION-CLIENT-ID>
   OIDC_CLIENT_SECRET=<CLIENT-SECRET>
   OIDC_SCOPES=openid email profile
   ```

5. Restart the backend; the login page shows the SSO button.

### Local development

Use the bundled `docker-compose.yml` (frontend + backend + Postgres). Copy
`.env.example` if present and adjust `SECRET_KEY` and `DATABASE_URL`.
