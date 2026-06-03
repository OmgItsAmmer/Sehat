import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { Icon } from "@/components/stitch/Icon";
import "@/theme/landing-theme.css";

const TRUST_STATS = [
  { value: "2 min", label: "Avg response time" },
  { value: "80%", label: "Cases handled autonomously" },
  { value: "P1 in 4s", label: "Emergency alert speed" },
  { value: "Urdu + English", label: "Bilingual support" },
] as const;

const PROBLEM_CARDS = [
  {
    emoji: "📬",
    title: "Message Overload",
    body: "Important patient queries get buried under routine questions.",
  },
  {
    emoji: "⏱",
    title: "Delayed Response",
    body: "Patients wait hours for simple answers or triage directions.",
  },
  {
    emoji: "😓",
    title: "Staff Burnout",
    body: "Front desk staff are overwhelmed, leading to mistakes and stress.",
  },
] as const;

const HOW_IT_WORKS = [
  { step: "1", title: "Patient sends message", body: "Initiates contact via WhatsApp or SMS." },
  { step: "2", title: "Sehat reads/classifies", body: "AI instantly analyzes intent and urgency." },
  { step: "3", title: "P1 alert in <4s", body: "Emergencies trigger immediate clinic notification." },
  { step: "4", title: "P2/P3 intake", body: "Routine cases get automated screening questions." },
  { step: "5", title: "Packaged history", body: "Symptoms are summarized for the doctor." },
  { step: "6", title: "Clean handoff", body: "Staff receives a neat, actionable ticket." },
] as const;

export function LandingPage() {
  return (
    <div className="landing-page flex min-h-dvh flex-col bg-background font-body-md text-on-background">
      <nav className="sticky top-0 z-50 w-full border-b border-outline-variant/10 bg-primary-container shadow-md">
        <div className="mx-auto flex h-20 max-w-container-max items-center justify-between px-margin-desktop">
          <div className="font-headline-md text-headline-md font-bold text-on-primary">
            Sehat | صحت
          </div>
          <div className="hidden items-center space-x-gutter md:flex">
            <a
              className="border-b-2 border-secondary-fixed pb-1 font-bold text-secondary-fixed transition-colors duration-200"
              href="#top"
            >
              Home
            </a>
            <a
              className="text-on-primary-container transition-colors duration-200 hover:text-secondary-fixed"
              href="#how-it-works"
            >
              How It Works
            </a>
            <a
              className="text-on-primary-container transition-colors duration-200 hover:text-secondary-fixed"
              href="#for-clinics"
            >
              For Clinics
            </a>
            <a
              className="text-on-primary-container transition-colors duration-200 hover:text-secondary-fixed"
              href="#contact"
            >
              Contact
            </a>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              className="hidden text-on-primary transition-colors duration-200 hover:text-secondary-fixed sm:inline"
            >
              Language Toggle
            </button>
            <Link
              to="/dashboard"
              className="rounded-lg bg-secondary px-4 py-2 font-headline-sm text-headline-sm text-on-secondary transition-all hover:opacity-80"
            >
              Open Dashboard
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-grow" id="top">
        <section className="relative overflow-hidden bg-primary-container bg-grid-pattern pt-stack-xl pb-stack-xl">
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="h-[800px] w-[800px] rounded-full bg-secondary-fixed opacity-10 blur-[120px]" />
          </div>
          <div className="relative z-10 mx-auto flex max-w-container-max flex-col items-center px-margin-desktop text-center">
            <div
              className="landing-hero-in mb-stack-md inline-flex items-center gap-2 rounded-full border border-secondary-fixed/30 bg-secondary-container/20 px-4 py-2 font-label-caps text-label-caps text-secondary-fixed"
              style={{ "--hero-delay": "0ms" } as CSSProperties}
            >
              <span className="h-2 w-2 rounded-full bg-secondary-fixed" />
              AI-Powered · Dr. Muhid Clinics · Lahore, Pakistan
            </div>
            <h1
              className="landing-hero-in mb-stack-md max-w-4xl font-headline-lg-mobile text-headline-lg-mobile tracking-tight text-on-primary md:font-headline-lg md:text-headline-lg"
              style={{ "--hero-delay": "80ms" } as CSSProperties}
            >
              Every patient message. Seen. Triaged. Routed. In seconds.
            </h1>
            <p
              className="landing-hero-in mb-stack-lg max-w-[600px] font-body-lg text-body-lg text-on-primary-container"
              style={{ "--hero-delay": "160ms" } as CSSProperties}
            >
              Sehat&apos;s AI handles your clinic&apos;s intake — asking the right questions, catching
              emergencies before they&apos;re missed, and handing Fatima only what needs a human touch.
            </p>
            <div
              className="landing-hero-in mb-stack-xl flex flex-col gap-4 sm:flex-row"
              style={{ "--hero-delay": "240ms" } as CSSProperties}
            >
              <Link
                to="/chat"
                className="rounded-full bg-secondary-fixed px-8 py-3 font-headline-sm text-headline-sm text-on-secondary-fixed shadow-[0_0_20px_rgba(130,247,223,0.3)] transition-all hover:opacity-90"
              >
                Chat Now →
              </Link>
              <a
                href="#how-it-works"
                className="rounded-full border border-on-primary px-8 py-3 font-headline-sm text-headline-sm text-on-primary transition-all hover:bg-on-primary/10"
              >
                See How It Works ↓
              </a>
            </div>

            <div
              className="landing-hero-in -rotate-3 w-full max-w-[420px] overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container-lowest shadow-2xl transition-transform duration-500 hover:rotate-0"
              style={{ "--hero-delay": "360ms" } as CSSProperties}
            >
              <div className="flex items-center justify-between bg-secondary px-4 py-3 text-on-secondary">
                <span className="font-headline-sm text-headline-sm">Sehat | صحت</span>
                <Icon name="verified_user" className="text-[18px]" />
              </div>
              <div className="flex flex-col gap-4 bg-surface-container-low p-6 text-left">
                <div className="max-w-[85%] self-start rounded-2xl rounded-tl-none border border-outline-variant/20 bg-surface-container-lowest p-3 font-body-sm text-body-sm text-on-surface shadow-sm">
                  Assalam o Alaikum! Dr. Muhid Clinics mein khush aamdeed. Apni takleef batayein.
                </div>
                <div className="max-w-[85%] self-end rounded-2xl rounded-tr-none bg-secondary-container p-3 font-body-sm text-body-sm text-on-secondary-container shadow-sm">
                  Mere abbu ko seene mein dard ho raha hai
                </div>
                <div className="flex max-w-[85%] gap-2 self-start rounded-2xl rounded-tl-none border border-error bg-error-container p-3 font-body-sm text-body-sm text-on-error-container shadow-sm">
                  <Icon name="warning" className="text-[20px] text-error" />
                  <span>
                    Yeh emergency ho sakti hai. Abhi 1122 call karein. Hum bhi Fatima ko alert kar
                    rahe hain.
                  </span>
                </div>
              </div>
            </div>
            <div
              className="landing-hero-in mt-4 inline-flex items-center gap-2 rounded-full bg-error-container px-3 py-1 font-label-caps text-label-caps text-on-error-container shadow-sm"
              style={{ "--hero-delay": "480ms" } as CSSProperties}
            >
              <Icon name="notifications_active" className="text-[16px]" />
              Fatima ko alert bhej diya
            </div>
          </div>
        </section>

        <section className="border-y border-outline-variant/10 bg-inverse-surface py-stack-md">
          <div className="mx-auto grid max-w-container-max grid-cols-2 gap-gutter divide-x divide-outline-variant/20 px-margin-desktop text-center md:grid-cols-4">
            {TRUST_STATS.map(({ value, label }, index) => (
              <ScrollReveal key={label} delay={index * 90} className="px-4">
                <div className="font-headline-md text-headline-md text-secondary-fixed">{value}</div>
                <div className="mt-1 font-label-caps text-label-caps text-on-primary-container">
                  {label}
                </div>
              </ScrollReveal>
            ))}
          </div>
        </section>

        <section className="bg-surface py-stack-xl">
          <div className="mx-auto max-w-container-max px-margin-desktop text-center">
            <ScrollReveal>
              <h2 className="mx-auto mb-stack-lg max-w-2xl font-headline-md text-headline-md text-on-surface">
                Your receptionist shouldn&apos;t be reading 34 messages before 9am.
              </h2>
            </ScrollReveal>
            <div className="grid grid-cols-1 gap-gutter md:grid-cols-3">
              {PROBLEM_CARDS.map(({ emoji, title, body }, index) => (
                <ScrollReveal key={title} delay={index * 100}>
                  <div className="flex flex-col items-center rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-stack-md text-center">
                    <div className="mb-4 text-4xl">{emoji}</div>
                    <h3 className="mb-2 font-headline-sm text-headline-sm text-on-surface">{title}</h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">{body}</p>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-t border-outline-variant/10 bg-surface-container-low py-stack-xl"
        >
          <div className="mx-auto max-w-container-max px-margin-desktop">
            <ScrollReveal>
              <h2 className="mb-stack-lg text-center font-headline-md text-headline-md text-on-surface">
                How Sehat Works
              </h2>
            </ScrollReveal>
            <div className="grid grid-cols-1 gap-gutter md:grid-cols-2 lg:grid-cols-3">
              {HOW_IT_WORKS.map(({ step, title, body }, index) => (
                <ScrollReveal key={step} delay={index * 80}>
                  <div className="flex items-start gap-4">
                    <div className="font-headline-lg text-headline-lg text-secondary opacity-80">
                      {step}
                    </div>
                    <div>
                      <h4 className="font-headline-sm text-headline-sm text-on-surface">{title}</h4>
                      <p className="mt-1 font-body-sm text-body-sm text-on-surface-variant">{body}</p>
                    </div>
                  </div>
                </ScrollReveal>
              ))}
            </div>
          </div>
        </section>

        <section
          id="for-clinics"
          className="relative overflow-hidden bg-primary-container py-stack-xl"
        >
          <div className="relative z-10 mx-auto max-w-container-max px-margin-desktop text-center">
            <ScrollReveal>
              <h2 className="mb-stack-sm font-headline-md text-headline-md text-on-primary">
                Built for Pakistani clinics. Ready in one day.
              </h2>
            </ScrollReveal>
            <ScrollReveal delay={100}>
              <p className="mx-auto mb-stack-lg max-w-2xl font-body-lg text-body-lg text-on-primary-container">
                No hardware. No IT team. Your clinic&apos;s WhatsApp number, our AI.
              </p>
            </ScrollReveal>
            <ScrollReveal delay={200}>
              <a
                id="contact"
                href="mailto:hello@sehat.ai"
                className="inline-block rounded-full bg-secondary-fixed px-8 py-4 font-headline-sm text-headline-sm text-on-secondary-fixed shadow-[0_0_20px_rgba(130,247,223,0.2)] transition-all hover:opacity-90"
              >
                Get Sehat for Your Clinic →
              </a>
            </ScrollReveal>
          </div>
        </section>
      </main>

      <footer className="w-full border-t border-outline-variant/10 bg-primary-container">
        <div className="mx-auto grid max-w-container-max grid-cols-1 gap-stack-lg px-margin-desktop py-stack-xl md:grid-cols-12">
          <ScrollReveal className="flex flex-col gap-4 md:col-span-4">
            <div className="font-headline-sm text-headline-sm font-bold text-on-primary">Sehat AI</div>
            <div className="font-body-sm text-body-sm text-on-primary-container">
              © 2024 Sehat AI. Built in Pakistan.
            </div>
          </ScrollReveal>
          <ScrollReveal delay={120} className="flex flex-wrap justify-start gap-x-12 gap-y-6 md:col-span-8 md:justify-end">
            <a
              className="font-body-sm text-body-sm text-on-primary-container transition-colors hover:text-secondary-fixed"
              href="#top"
            >
              Product
            </a>
            <a
              className="font-body-sm text-body-sm text-on-primary-container transition-colors hover:text-secondary-fixed"
              href="#for-clinics"
            >
              Clinic
            </a>
            <a
              className="font-body-sm text-body-sm text-on-primary-container transition-colors hover:text-secondary-fixed"
              href="#contact"
            >
              Legal
            </a>
          </ScrollReveal>
        </div>
      </footer>
    </div>
  );
}
