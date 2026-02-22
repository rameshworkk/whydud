import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Whydud — Don't Buy a Dud",
  description: "India's product intelligence platform. Check DudScore, price history, and fake review detection before you buy.",
};

export default function HomePage() {
  return (
    <>
      <Header />
      <main>
        {/* Hero */}
        <section className="mx-auto max-w-4xl px-4 py-24 text-center">
          <h1 className="text-5xl font-black tracking-tight leading-tight">
            Don&apos;t buy a dud.
          </h1>
          <p className="mt-4 text-xl text-muted-foreground max-w-2xl mx-auto">
            India&apos;s first product intelligence platform. Check real prices, detect fake reviews,
            and get a personalized deal — before you buy.
          </p>

          {/* TODO Sprint 1 Week 3: Replace with live SearchBar component */}
          <div className="mt-8 flex gap-2 max-w-xl mx-auto">
            <input
              type="search"
              placeholder='Try "Samsung Galaxy Buds" or "Crompton AC"'
              className="flex-1 rounded-full border bg-muted px-5 py-3 text-base outline-none"
            />
            <button className="rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground">
              Search
            </button>
          </div>
        </section>

        {/* Feature teasers */}
        <section className="mx-auto max-w-6xl px-4 py-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            { icon: "🎯", title: "DudScore", desc: "Trust-adjusted product score combining genuine reviews, price fairness, and fraud signals." },
            { icon: "📈", title: "Price History", desc: "See real price history powered by TimescaleDB. Spot fake 60%-off deals instantly." },
            { icon: "💳", title: "Smart Payment Optimizer", desc: "Get personalized card × marketplace combos. \"Save ₹1,500 with your HDFC card on Amazon.\"" },
            { icon: "📧", title: "@whyd.xyz Inbox", desc: "Get a free @whyd.xyz email. All shopping emails auto-parsed into your dashboard." },
            { icon: "🔍", title: "Fake Review Detection", desc: "Detect copy-paste reviews, rating bursts, and review farm patterns automatically." },
            { icon: "⚡", title: "Blockbuster Deals", desc: "Error pricing and genuine discounts — verified against real price history." },
          ].map((f) => (
            <div key={f.title} className="rounded-xl border bg-card p-6">
              <span className="text-3xl">{f.icon}</span>
              <h3 className="mt-3 font-bold text-lg">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </section>
      </main>
      <Footer />
    </>
  );
}
