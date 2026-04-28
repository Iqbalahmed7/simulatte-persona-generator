/**
 * /terms — Terms of use for mind.simulatte.io.
 */
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms — Simulatte / The Mind",
  description: "What you can and can't do here.",
};

const UPDATED = "April 2026";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-void text-parchment">
      <div className="max-w-2xl mx-auto px-6 py-16">
        <Link
          href="/"
          className="text-[11px] font-mono uppercase tracking-[0.18em] text-static hover:text-signal"
        >
          ← Simulatte / The Mind
        </Link>
        <h1 className="font-condensed font-bold text-5xl mt-8 mb-2">Terms</h1>
        <p className="text-[11px] font-mono text-static uppercase tracking-[0.18em] mb-12">
          Last updated {UPDATED}
        </p>

        <Section title="What this is">
          <P>
            The Mind is a tool for simulating how a behaviourally coherent
            synthetic person might respond to a product, message, or question.
            It is operated by Simulatte. Using the service means you agree to
            what&#x2019;s on this page.
          </P>
        </Section>

        <Section title="Who can use it">
          <P>
            You must be 18 or older. You must not share your account.
            We may suspend an account for abuse, attempted exfiltration, or
            anything that puts the service at risk for other users.
          </P>
        </Section>

        <Section title="What you can do">
          <P>
            Generate personas. Probe and chat with them. Share persona URLs.
            Use the simulated reactions in your own work — internal docs,
            pitch decks, product reviews. We don&#x2019;t take ownership of
            what you generate; the briefs and resulting personas are yours
            to use within these terms.
          </P>
        </Section>

        <Section title="What you can&#x2019;t">
          <P>
            <Bad>Don&#x2019;t simulate real, named individuals.</Bad>
            Generic descriptions of customer types are fine; building a
            persona to impersonate or harass a specific real person is not.
          </P>
          <P>
            <Bad>Don&#x2019;t simulate minors.</Bad>
            All personas must be 18+. The system blocks underage briefs
            automatically.
          </P>
          <P>
            <Bad>Don&#x2019;t use it for sexual or NSFW content.</Bad>
            This is for buyer / consumer simulation, not adult fiction.
          </P>
          <P>
            <Bad>Don&#x2019;t scrape, automate, or resell the API.</Bad>
            One human per account, used at human pace. If you want
            programmatic access, email us.
          </P>
          <P>
            <Bad>Don&#x2019;t pretend a generated persona is a real person.</Bad>
            If you publish probe results or quotes from a chat, label them
            as Simulatte-generated.
          </P>
        </Section>

        <Section title="What we provide and what we don&#x2019;t">
          <P>
            The personas are simulations. They are calibrated against real
            human behavioural patterns but they are not market research, not
            statistically representative, and not a substitute for talking to
            actual customers. Treat the output as a fast first read, not a
            verdict.
          </P>
          <P>
            We aim for high uptime but make no guarantee. If the service is
            down or a generation fails, we&#x2019;ll refund the affected
            allowance.
          </P>
        </Section>

        <Section title="Allowances and pricing">
          <P>
            Free accounts get a fixed weekly allowance for persona generation,
            probes, and chats. The current limits are visible on your
            dashboard. We may adjust them as the service evolves; we won&#x2019;t
            cut existing users mid-week without notice.
          </P>
        </Section>

        <Section title="Termination">
          <P>
            You can delete your account any time by emailing{" "}
            <a href="mailto:mind@simulatte.io" className="text-signal hover:underline">
              mind@simulatte.io
            </a>
            . We can suspend or terminate accounts that violate these terms,
            with notice when reasonable.
          </P>
        </Section>

        <Section title="Liability">
          <P>
            To the extent allowed by law, our liability is capped at the
            amount you&#x2019;ve paid us in the prior twelve months. (Most
            users are on the free tier, so that&#x2019;s zero.)
          </P>
        </Section>

        <Section title="Contact">
          <P>
            Questions, requests, complaints:{" "}
            <a href="mailto:mind@simulatte.io" className="text-signal hover:underline">
              mind@simulatte.io
            </a>
            .
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

function Bad({ children }: { children: React.ReactNode }) {
  return <span className="text-parchment font-semibold">{children}</span>;
}
