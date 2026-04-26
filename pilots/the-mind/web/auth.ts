/**
 * auth.ts — Auth.js v5 Node-runtime entry point.
 *
 * Imports Edge-safe config from auth.config.ts, then adds the pg adapter
 * and the custom Resend magic-link email. This file must NEVER be imported
 * from middleware.ts — Edge runtime cannot load pg (net/tls/crypto/dns).
 *
 * Required env vars (Vercel):
 *   NEXTAUTH_URL            https://mind.simulatte.io
 *   NEXTAUTH_SECRET         32+ char random string
 *   GOOGLE_CLIENT_ID        from Google Cloud Console
 *   GOOGLE_CLIENT_SECRET    from Google Cloud Console
 *   AUTH_RESEND_KEY         Resend API key
 *   EMAIL_FROM              noreply@mind.simulatte.io
 *   DATABASE_URL            postgresql://...
 */
import NextAuth from "next-auth";
import Resend from "next-auth/providers/resend";
import PostgresAdapter from "@auth/pg-adapter";
import { Pool } from "pg";
import { authConfig } from "./auth.config";

// ── Postgres pool ─────────────────────────────────────────────────────────
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === "production"
    ? { rejectUnauthorized: false }
    : false,
  max: 3,
});

// ── Magic-link HTML email ─────────────────────────────────────────────────
function magicLinkHtml({ url }: { url: string }): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sign in to The Mind</title>
  <style>
    body { margin: 0; padding: 0; background: #0a0a0a; font-family: 'Helvetica Neue', Arial, sans-serif; }
    .wrapper { max-width: 480px; margin: 40px auto; background: #0a0a0a; border: 1px solid rgba(240,230,210,0.12); border-radius: 4px; overflow: hidden; }
    .header { padding: 32px 40px 24px; border-bottom: 1px solid rgba(240,230,210,0.08); }
    .logo { font-size: 18px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #f0e6d2; }
    .byline { font-size: 10px; letter-spacing: 0.12em; color: rgba(240,230,210,0.5); margin-top: 2px; font-family: 'Courier New', monospace; }
    .body { padding: 32px 40px; }
    .headline { font-size: 22px; font-weight: 700; color: #f0e6d2; margin: 0 0 12px; line-height: 1.3; }
    .sub { font-size: 14px; color: rgba(240,230,210,0.6); margin: 0 0 28px; line-height: 1.6; }
    .btn { display: inline-block; background: #00c896; color: #0a0a0a; text-decoration: none; font-weight: 700; font-size: 14px; letter-spacing: 0.06em; padding: 14px 32px; border-radius: 2px; }
    .divider { border: none; border-top: 1px solid rgba(240,230,210,0.08); margin: 28px 0; }
    .url-label { font-size: 11px; color: rgba(240,230,210,0.4); margin: 0 0 6px; font-family: 'Courier New', monospace; letter-spacing: 0.06em; text-transform: uppercase; }
    .url-box { background: rgba(240,230,210,0.04); border: 1px solid rgba(240,230,210,0.08); border-radius: 2px; padding: 10px 14px; word-break: break-all; }
    .url-text { font-size: 11px; color: rgba(240,230,210,0.5); font-family: 'Courier New', monospace; }
    .footer { padding: 20px 40px; border-top: 1px solid rgba(240,230,210,0.08); }
    .footer-text { font-size: 11px; color: rgba(240,230,210,0.3); line-height: 1.6; }
    .expiry { font-size: 11px; color: rgba(240,230,210,0.35); margin-top: 8px; font-family: 'Courier New', monospace; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="logo">The Mind</div>
      <div class="byline">by Simulatte</div>
    </div>
    <div class="body">
      <p class="headline">Sign in to The Mind</p>
      <p class="sub">Click below to sign in. This link works once and expires in 10 minutes.</p>
      <a href="${url}" class="btn">Sign in →</a>
      <hr class="divider" />
      <p class="url-label">Or paste this URL</p>
      <div class="url-box">
        <span class="url-text">${url}</span>
      </div>
      <p class="expiry">Expires in 10 minutes · Single use</p>
    </div>
    <div class="footer">
      <p class="footer-text">
        You received this because someone requested a sign-in link for this email address at mind.simulatte.io.
        If you did not request this, you can safely ignore it.
      </p>
    </div>
  </div>
</body>
</html>`;
}

// ── Auth.js config (Node runtime, with adapter + custom email) ────────────
export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  adapter: PostgresAdapter(pool),
  providers: [
    // Override Resend provider here to add custom sendVerificationRequest.
    // Google stays as-is from authConfig.providers; we spread authConfig
    // but replace providers entirely so we get both with the override.
    ...(authConfig.providers as []).filter(
      (p: { id?: string }) => p.id !== "resend"
    ),
    Resend({
      apiKey: process.env.AUTH_RESEND_KEY!,
      from: process.env.EMAIL_FROM ?? "noreply@mind.simulatte.io",
      name: "The Mind",
      sendVerificationRequest: async ({ identifier, url, provider }) => {
        const { Resend: ResendClient } = await import("resend");
        const resend = new ResendClient(provider.apiKey);
        await resend.emails.send({
          from: provider.from ?? "noreply@mind.simulatte.io",
          to: identifier,
          subject: "Sign in to The Mind",
          html: magicLinkHtml({ url }),
        });
      },
    }),
  ],
});
