/**
 * /welcome — public landing for visitors without a session or invite cookie.
 *
 * Single primary action: sign in with Google. Returning users on a new
 * device land here and click through. New users without a code also
 * sign in (creating a pending account) and see the waitlist screen
 * inside the app where they can paste a code or request access.
 */
import Link from "next/link";

export default function WelcomePage(props: {
  searchParams: Promise<{ from?: string }>;
}) {
  return <WelcomeView searchParamsPromise={props.searchParams} />;
}

async function WelcomeView({ searchParamsPromise }: {
  searchParamsPromise: Promise<{ from?: string }>;
}) {
  const sp = await searchParamsPromise;
  const callbackUrl = sp.from && sp.from.startsWith("/") ? sp.from : "/";
  const signInHref = `/sign-in?callbackUrl=${encodeURIComponent(callbackUrl)}`;

  return (
    <div className="min-h-screen bg-void text-parchment flex flex-col">
      <header className="border-b border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link href="/welcome" className="font-condensed font-black text-lg uppercase tracking-wider">
            The Mind
            <span className="ml-2 text-[10px] font-mono text-parchment/40 tracking-[0.18em]">
              BY SIMULATTE
            </span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-xl w-full text-center">
          <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-4">
            PRIVATE LAUNCH
          </p>
          <h1 className="font-condensed font-black text-5xl md:text-6xl leading-[0.96] mb-6">
            The decision <span className="text-signal">infrastructure</span> behind real consumer behaviour.
          </h1>
          <p className="text-parchment/72 text-lg leading-[1.78] mb-10">
            Sign in with Google to continue. If you don&#x2019;t have an invite,
            we&#x2019;ll add you to the waitlist.
          </p>

          <Link
            href={signInHref}
            className="inline-block bg-signal text-void font-condensed font-bold uppercase tracking-wider px-8 py-4"
          >
            Sign in with Google →
          </Link>

          <p className="mt-10 text-parchment/60 text-sm">
            Have an invite link? Just open it — you&#x2019;ll be sent here
            with access pre-approved.
          </p>
          <p className="mt-2 text-parchment/60 text-sm">
            Need an invite?{" "}
            <a
              href="mailto:mind@simulatte.io?subject=Request%20access%20to%20The%20Mind"
              className="text-signal underline underline-offset-4"
            >
              mind@simulatte.io
            </a>
          </p>
        </div>
      </main>

      <footer className="border-t border-parchment/10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <span className="text-[10px] font-mono text-parchment/40 tracking-[0.18em]">
            SIMULATTE · CONFIDENTIAL
          </span>
          <a
            href="https://simulatte.io"
            className="text-[10px] font-mono text-parchment/40 hover:text-signal tracking-[0.18em]"
          >
            SIMULATTE.IO
          </a>
        </div>
      </footer>
    </div>
  );
}
