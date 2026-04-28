/**
 * /invite/[code] — invite-link redemption.
 *
 * Server component. Validates the code against FastAPI; renders a tiny
 * HTML splash with proper Open Graph metadata so WhatsApp / LinkedIn /
 * iMessage show a brand-locked preview card when someone shares the
 * link. The splash includes a meta-refresh + JS push to
 * /invite/[code]/redeem, where the cookie + localStorage get set.
 *
 * We deliberately don't use a server-side redirect() here because that
 * would return a 307 with no HTML body, and crawlers wouldn't see the
 * og:image / og:title tags.
 *
 * Invalid / exhausted / inactive codes render an error page with a
 * mailto fallback.
 */
import type { Metadata } from "next";
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

export async function generateMetadata(props: {
  params: Promise<{ code: string }>;
}): Promise<Metadata> {
  const { code } = await props.params;
  const title = "You're invited to The Mind";
  const description =
    "Talk to a person who doesn't exist. The Mind generates a behaviourally coherent synthetic person from a paragraph — then lets you simulate any decision they'd make.";
  const url = `https://mind.simulatte.io/invite/${encodeURIComponent(code)}`;
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: "The Mind",
      type: "website",
      // The opengraph-image.tsx in this same segment is auto-attached
      // by Next.js, so we don't need to spell out images here.
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    robots: { index: false, follow: false },
  };
}

export default async function InvitePage(props: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await props.params;
  const result = await checkCode(code);

  if (result.valid) {
    const target = `/invite/${encodeURIComponent(code)}/redeem`;
    return (
      <html lang="en">
        <head>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width,initial-scale=1" />
          <meta httpEquiv="refresh" content={`0;url=${target}`} />
          <title>You&apos;re invited to The Mind</title>
        </head>
        <body
          style={{
            margin: 0,
            background: "#050505",
            color: "#E9E6DF",
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 11,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          Redeeming invite…
          <script
            // Belt-and-braces — meta refresh fires anyway, but JS gets
            // there a few ms faster on real browsers.
            dangerouslySetInnerHTML={{
              __html: `window.location.replace(${JSON.stringify(target)});`,
            }}
          />
        </body>
      </html>
    );
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
