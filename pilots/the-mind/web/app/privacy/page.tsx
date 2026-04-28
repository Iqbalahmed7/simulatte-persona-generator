/**
 * /privacy — Privacy notice for mind.simulatte.io.
 *
 * Required for the Google OAuth consent screen and for credibility
 * when sharing the URL externally. Plain language, no marketing fluff.
 */
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy — Simulatte / The Mind",
  description: "What we collect, what we don't, and how to delete it.",
};

const UPDATED = "April 2026";
const CONTACT = "mind@simulatte.io";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-void text-parchment">
      <div className="max-w-2xl mx-auto px-6 py-16">
        <Link
          href="/"
          className="text-[11px] font-mono uppercase tracking-[0.18em] text-static hover:text-signal"
        >
          ← Simulatte / The Mind
        </Link>
        <h1 className="font-condensed font-bold text-5xl mt-8 mb-2">
          Privacy
        </h1>
        <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-12">
          Last updated {UPDATED}
        </p>

        <Section title="What we collect">
          <P>
            When you sign in, Google sends us your email address, your name, and
            your profile picture URL. We store those, plus an internal user ID,
            in our database. Nothing else from your Google account.
          </P>
          <P>
            When you generate a persona, ask a persona a question, or run a
            probe, we log the action against your user ID — what you did, when,
            and on which persona. We use this to enforce your weekly allowance
            and to power your &quot;your personas&quot; list. The text you submit
            (your persona brief, your chat message, your product description)
            is sent to Anthropic&#x2019;s Claude API and to fal.ai for portrait
            generation.
          </P>
          <P>
            We log basic technical events: IP address, browser user-agent, and
            request paths, retained for 30 days for security and rate-limiting.
          </P>
        </Section>

        <Section title="What we don&#x2019;t">
          <P>
            We don&#x2019;t use third-party advertising trackers. There&#x2019;s
            no Google Analytics, no Facebook Pixel, no LinkedIn Insight tag.
          </P>
          <P>
            We don&#x2019;t sell or share your data with anyone outside our
            processing infrastructure (Anthropic, fal.ai, Resend for email,
            Vercel for hosting, Railway for the API and database).
          </P>
          <P>
            Generated personas are not real people. They&#x2019;re behaviourally
            coherent simulations built from the brief you wrote. We don&#x2019;t
            train models on your data.
          </P>
        </Section>

        <Section title="Subprocessors">
          <P>
            <Sub name="Anthropic" purpose="LLM calls for persona generation, chat, and probe responses" />
            <Sub name="fal.ai" purpose="image generation for persona portraits" />
            <Sub name="Vercel" purpose="frontend hosting and edge caching" />
            <Sub name="Railway" purpose="API server and Postgres database" />
            <Sub name="Resend" purpose="transactional email (waitlist, approval)" />
            <Sub name="Google" purpose="OAuth sign-in" />
          </P>
        </Section>

        <Section title="Your rights">
          <P>
            Email <Mail /> to:
          </P>
          <ul className="list-none space-y-2 ml-0 mt-3">
            <li className="text-parchment/85">
              <span className="text-signal">·</span> get a copy of everything we
              hold on your account
            </li>
            <li className="text-parchment/85">
              <span className="text-signal">·</span> delete your account and all
              your generated personas
            </li>
            <li className="text-parchment/85">
              <span className="text-signal">·</span> correct inaccurate
              information
            </li>
            <li className="text-parchment/85">
              <span className="text-signal">·</span> ask anything about how your
              data is handled
            </li>
          </ul>
          <P>
            We respond within 30 days. Usually much faster — this is a small
            operation.
          </P>
        </Section>

        <Section title="Cookies">
          <P>
            One cookie: an Auth.js session token, set when you sign in, scoped
            to mind.simulatte.io. Cleared when you sign out. No third-party
            cookies.
          </P>
        </Section>

        <Section title="Children">
          <P>
            The Mind is not for users under 18. Personas built around minors
            are blocked at submission. If we learn a user is under 18, we
            delete the account.
          </P>
        </Section>

        <Section title="Changes">
          <P>
            If we materially change anything here, the &quot;last updated&quot;
            date above will move and active users will see a notice on next
            sign-in. The current version always lives at this URL.
          </P>
        </Section>

        <Section title="Contact">
          <P>
            <Mail /> · Simulatte / The Mind
          </P>
        </Section>

        <p className="mt-16 text-[11px] font-mono text-static/60 uppercase tracking-[0.18em]">
          Created with Simulatte
        </p>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="font-condensed font-bold text-2xl mb-4">{title}</h2>
      <div className="space-y-4 text-parchment/85 leading-relaxed">{children}</div>
    </section>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p>{children}</p>;
}

function Sub({ name, purpose }: { name: string; purpose: string }) {
  return (
    <span className="block">
      <span className="text-parchment">{name}</span>
      <span className="text-parchment/60"> — {purpose}</span>
    </span>
  );
}

function Mail() {
  return (
    <a href="mailto:mind@simulatte.io" className="text-signal hover:underline">
      mind@simulatte.io
    </a>
  );
}
