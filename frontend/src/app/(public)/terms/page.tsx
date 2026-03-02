import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Whydud terms of service and usage agreement.",
};

export default function TermsPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-2">Terms of Service</h1>
        <p className="text-sm text-[#94A3B8] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#475569] leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">1. Acceptance of Terms</h2>
            <p>
              By accessing or using the Whydud platform (&quot;Service&quot;), you agree
              to be bound by these Terms of Service. If you do not agree, please do
              not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">2. Description of Service</h2>
            <p>
              Whydud provides product intelligence, price tracking, review
              aggregation, and comparison tools for products listed on Indian
              e-commerce marketplaces. Prices displayed are sourced from public
              listings and may not reflect real-time availability.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">3. User Accounts</h2>
            <p>
              You are responsible for maintaining the confidentiality of your account
              credentials. You agree to provide accurate information during
              registration and to keep it current.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">4. User Content</h2>
            <p>
              Reviews and discussions you submit must be honest, original, and comply
              with applicable laws. Whydud reserves the right to remove content that
              violates these terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">5. Affiliate Disclosure</h2>
            <p>
              Some links on Whydud are affiliate links. We may earn a commission when
              you make a purchase through these links, at no additional cost to you.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">6. Limitation of Liability</h2>
            <p>
              Whydud is provided &quot;as is&quot;. We do not guarantee the accuracy
              of prices, reviews, or scores. Purchase decisions are made at your own
              discretion.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">7. Contact</h2>
            <p>
              For questions about these terms, please reach out via our{" "}
              <a href="/contact" className="text-[#F97316] hover:underline">
                Contact page
              </a>
              .
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
