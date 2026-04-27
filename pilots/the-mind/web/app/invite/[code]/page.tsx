/**
 * /invite/[code] — code redemption landing.
 *
 * Server component that hits FastAPI /invites/{code}/check, sets the
 * `invite_ok` cookie when the code is valid, and renders a small confirm
 * page with a CTA to /sign-in. We don't auto-redirect — that lets the user
 * see "you're in" and choose when to sign in.
 *
 * Invalid codes show a clear error and a link back to /welcome.
 */
import { cookies } from "next/headers";
import Link from "next/link";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

async function checkCode(code: string): Promise<{
  valid: boolean;
  label?: string | null;
  reason?: string;
  used_count?: number;
  max_uses?: number | null;
}> {
  try {
    const res = await fetch(`${API}/invites/${encodeURIComponent(code)}/check`, {
      cache: "no-store",
    });
    if (!res.ok) return { valid: false, reason: "server_error" };
    return await res.json();
  } catch {
    return { valid: false, reason: "network_error" };
  }
}

export default async function InvitePage(props: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await props.params;
  const result = await checkCode(code);

  // Set the cookie if valid. 60-day expiry — same as Auth.js session.
  if (result.valid) {
    const jar = await cookies();
    jar.set("invite_ok", code.toUpperCase(), {
      maxAge: 60 * 60 * 24 * 60,
      httpOnly: false,
      sameSite: "lax",
      path: "/",
      secure: process.env.NODE_ENV === "production",
    });
  }

  return (
    <div className="min-h-screen bg-void text-parchment flex items-center justify-center px-6">
      <div className="max-w-xl w-full">
        {result.valid ? (
          <>
            <p className="text-[11px] font-mono text-signal uppercase tracking-[0.18em] mb-4">
              ACCESS GRANTED
            </p>
            <h1 className="font-condensed font-black text-5xl leading-[0.96] mb-6">
              You&#x2019;re <span className="text-signal">in.</span>
            </h1>
            <p className="text-parchment/72 text-lg leading-[1.78] mb-8">
              {result.label ? (
                <>
                  Code <span className="font-mono text-parchment">{code.toUpperCase()}</span>
                  {" "}({result.label}) verified. Sign in with Google to start
                  generating personas.
                </>
              ) : (
                <>
                  Code <span className="font-mono text-parchment">{code.toUpperCase()}</span>
                  {" "}verified. Sign in with Google to start generating personas.
                </>
              )}
            </p>
            <Link
              href="/sign-in?callbackUrl=/"
              className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3"
            >
              Sign in with Google
            </Link>
          </>
        ) : (
          <>
            <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-4">
              INVITE CODE
            </p>
            <h1 className="font-condensed font-black text-5xl leading-[0.96] mb-6">
              That code didn&#x2019;t check out.
            </h1>
            <p className="text-parchment/72 text-lg leading-[1.78] mb-8">
              {result.reason === "exhausted"
                ? "This code has been fully redeemed. Ask whoever shared it for a fresh one."
                : result.reason === "inactive"
                ? "This code is no longer active."
                : "We couldn't find that invite code. Double-check the spelling, or request access from mind@simulatte.io."}
            </p>
            <div className="flex gap-4">
              <Link
                href="/welcome"
                className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3"
              >
                Back to welcome
              </Link>
              <a
                href="mailto:mind@simulatte.io?subject=Request%20access%20to%20The%20Mind"
                className="inline-block border border-parchment/20 text-parchment font-condensed font-bold uppercase tracking-wider px-6 py-3"
              >
                Email us
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
