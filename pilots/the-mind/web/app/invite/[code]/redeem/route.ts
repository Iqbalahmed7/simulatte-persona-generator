/**
 * GET /invite/[code]/redeem — sets invite_ok cookie + stashes code in
 * localStorage, then redirects to /sign-in.
 *
 * Why this isn't a plain server-side redirect: cookies sometimes get
 * dropped during the Google OAuth round-trip (sameSite=lax should keep
 * them, but some browsers / extensions are strict). localStorage is a
 * belt-and-braces backup that's read by the Waitlist component if the
 * cookie went missing.
 *
 * We can't write localStorage from a Route Handler directly, so we
 * return a tiny HTML page that does the write then navigates. Total
 * time to first useful work: ~30ms.
 */
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ code: string }> },
) {
  const { code } = await ctx.params;
  const upper = code.toUpperCase();

  // Cookie set via headers (same-origin, 60-day TTL).
  const jar = await cookies();
  jar.set("invite_ok", upper, {
    maxAge: 60 * 60 * 24 * 60,
    httpOnly: false,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });

  // JSON.stringify avoids any HTML/JS injection from the path param.
  const safe = JSON.stringify(upper);
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Redeeming…</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#050505;color:#E9E6DF;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;letter-spacing:.18em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;min-height:100vh}</style></head><body>Redeeming invite…<script>try{localStorage.setItem('invite_ok',${safe});}catch(e){}window.location.replace('/sign-in?callbackUrl=/dashboard');</script></body></html>`;

  return new Response(html, {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
