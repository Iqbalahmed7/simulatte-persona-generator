/**
 * /invite/[code] — invite-link redemption.
 *
 * Server component. Validates the code against FastAPI; if valid, sets
 * the `invite_ok` cookie and **redirects** the visitor straight to
 * /sign-in (no interstitial click). The Auth.js sign-in page picks up
 * the cookie; once they finish Google OAuth, our backend's
 * get_current_user activates the pending account, mints a personal
 * reshare code, and records invited_by_user_id from this code.
 *
 * Invalid / exhausted / inactive codes render an error page with a
 * mailto fallback so we don't dead-end the visitor.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

async function checkCode(code: string): Promise<{
  valid: boolean;
  label?: string | null;
  reason?: string;
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

  if (result.valid) {
    const jar = await cookies();
    jar.set("invite_ok", code.toUpperCase(), {
      maxAge: 60 * 60 * 24 * 60, // 60 days
      httpOnly: false,
      sameSite: "lax",
      path: "/",
      secure: process.env.NODE_ENV === "production",
    });
    redirect("/sign-in?callbackUrl=/");
  }

  const reasonCopy =
    result.reason === "exhausted"
      ? "This invite has been fully redeemed. Ask whoever shared it for a fresh one."
      : result.reason === "inactive"
      ? "This invite is no longer active."
      : "We couldn't find that invite. Double-check the link, or request access from mind@simulatte.io.";

  return (
    <div className="min-h-screen bg-void text-parchment flex items-center justify-center px-6">
      <div className="max-w-xl w-full">
        <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-4">
          INVITE
        </p>
        <h1 className="font-condensed font-black text-5xl leading-[0.96] mb-6">
          That invite didn&#x2019;t check out.
        </h1>
        <p className="text-parchment/72 text-lg leading-[1.78] mb-8">
          {reasonCopy}
        </p>
        <div className="flex gap-4 flex-wrap">
          <Link
            href="/welcome"
            className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-6 py-3"
          >
            Sign in instead
          </Link>
          <a
            href="mailto:mind@simulatte.io?subject=Request%20access%20to%20The%20Mind"
            className="inline-block border border-parchment/20 text-parchment font-condensed font-bold uppercase tracking-wider px-6 py-3"
          >
            Email us
          </a>
        </div>
      </div>
    </div>
  );
}
