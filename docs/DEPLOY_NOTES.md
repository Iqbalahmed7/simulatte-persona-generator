# Phase 3a Deploy Notes — Auth + Postgres + Allowances

## Required env vars

### Vercel (frontend — mind.simulatte.io)

| Variable | Value | Notes |
|---|---|---|
| `NEXTAUTH_URL` | `https://mind.simulatte.io` | Must match production URL exactly |
| `NEXTAUTH_SECRET` | 32+ char random string | **Share this exact value with Railway** |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console | Already exists per Iqbal |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console | Already exists per Iqbal |
| `AUTH_RESEND_KEY` | Resend API key (re_...) | From resend.com dashboard |
| `EMAIL_FROM` | `noreply@mind.simulatte.io` | Domain must be verified in Resend |
| `DATABASE_URL` | `postgresql://postgres:PASSWORD@postgres.railway.internal:5432/railway` | Same as Railway backend |
| `NEXT_PUBLIC_API_URL` | `https://the-mind-api-production.up.railway.app` | Already set |

### Railway (backend — the-mind-api service)

| Variable | Value | Notes |
|---|---|---|
| `NEXTAUTH_SECRET` | **Same value as Vercel** | Backend verifies JWTs with this |
| `DATABASE_URL` | `${{ Postgres.DATABASE_URL }}` | Already wired via Railway reference |

## NEXTAUTH_SECRET generation

Run this locally to generate a secure secret:
```bash
openssl rand -base64 32
```
Set the **same output** in both Vercel and Railway.

## Resend domain verification

Before magic links will deliver, verify `mind.simulatte.io` in your Resend account:
1. Go to resend.com → Domains → Add Domain
2. Add `mind.simulatte.io`
3. Add the DKIM/SPF/DMARC DNS records in your DNS provider
4. Wait for verification (usually <5 minutes on Cloudflare)

If the domain is not verified yet, magic link emails will fail silently. Google OAuth will still work.

## Google OAuth callback URL

In Google Cloud Console → Credentials → your OAuth client, add:
```
https://mind.simulatte.io/api/auth/callback/google
```

## Database migrations

After first deploy to Railway, run migrations once:
```bash
# SSH into Railway service shell, or run locally pointing at Railway DB:
cd pilots/the-mind/api
DATABASE_URL="postgresql://..." alembic upgrade head
```

The `alembic.ini` and `alembic/` directory are in `pilots/the-mind/api/`.

## Verify deploy

1. Visit https://mind.simulatte.io/generate — should redirect to /sign-in
2. Sign in with Google — should land on /generate
3. Visit /generate — AllowanceCounter badge should appear showing "Personas 0/1 · Probes 0/3 · Chats 0/5"
4. Generate a persona — counter should increment to "Personas 1/1"
5. Try to generate again — should see hard-wall modal with Calendly CTA
6. Try magic link sign-in — check inbox for branded email

## Auth notes

- `NEXTAUTH_SECRET` is the HS256 signing key for all JWTs. It must be identical on both services.
- The frontend sends the JWT as `Authorization: Bearer <token>` header on all gated API calls.
- FastAPI reads this in `auth.py:get_current_user()` and verifies with `PyJWT`.
- Exemplar chat (`/[slug]/chat`) remains **public** — no auth required. These are the demo personas.

## Cost impact

Phase 3a adds no per-request LLM cost. The Postgres add-on is ~$5/mo on Railway.
