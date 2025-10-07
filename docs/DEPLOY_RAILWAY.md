# Deploy to Railway (First without OAuth, then enable OAuth)

This guide gets Sparky running on Railway without Google OAuth first (so you can attach a custom domain), then enables OAuth once the domain is live.

## 1) Prepare repo

- Ensure these files exist (already in repo):
  - `Procfile` → `web: python -m app.main`
  - Health route at `GET /health` (returns `{ "status": "ok" }`)
- Push latest code to GitHub.

## 2) Create service on Railway

- In Railway: New Project → Deploy from GitHub → choose this repo.
- Build will run `pip install -r requirements.txt`.
- Start command is read from `Procfile`. If not detected, set: `python -m app.main`.

## 3) Set environment variables (OAuth disabled)

Set only these variables to get a working app without OAuth:

- `OPENAI_API_KEY` = your OpenAI key
- `SUPABASE_URL` = https://<project>.supabase.co
- `SUPABASE_KEY` = your Supabase anon key
- `JWT_SECRET` = random 64-hex string (keep consistent across deploys)
- `DISABLE_OAUTH` = `true` (critical for first deploy)

Do NOT set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, or `OAUTH_REDIRECT_URI` yet.

## 4) Health checks

- In Railway → Settings → Health Checks
- Set HTTP Health Check Path to `/health`.

## 5) Deploy and verify

- Trigger a deploy or push to the branch.
- Check logs for:
  - `Running on http://0.0.0.0:<PORT>`
- Open the service URL and hit `/health` → should return `{"status":"ok"}`.

## 6) Add custom domain

- Railway → Domains → Add Custom Domain → follow DNS instructions.
- Wait for domain to be active (HTTPS ready).

## 7) Enable OAuth

Now that your custom domain is live, configure Google OAuth:

In Google Cloud Console → APIs & Services → Credentials
- Authorized JavaScript origins: `https://YOUR_DOMAIN`
- Authorized redirect URIs: `https://YOUR_DOMAIN/api/auth/google/callback`

In Railway → Variables, add:
- `GOOGLE_CLIENT_ID` = your client ID
- `GOOGLE_CLIENT_SECRET` = your client secret
- `OAUTH_REDIRECT_URI` = `https://YOUR_DOMAIN/api/auth/google/callback`
- Set `DISABLE_OAUTH` = `false`

Redeploy. The login flow should now work:
- GET `/` → login page
- GET `/api/auth/google` → redirects to Google
- GET `/api/auth/google/callback` → establishes session and redirects to `/chat`

## Notes

- The app enforces auth on API routes via JWT stored in encrypted cookies.
- Without OAuth (when `DISABLE_OAUTH=true`), the login flow is disabled and API routes that require auth will return 401.
- Keep your `JWT_SECRET` stable across deploys to avoid invalidating sessions on every deploy.
- If your platform requires a different port binding style, Sparky reads `PORT` from the environment automatically.
