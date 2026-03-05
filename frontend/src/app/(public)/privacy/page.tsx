import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Whydud privacy policy — how we collect and use your data.",
};

export default function PrivacyPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-2">Privacy Policy</h1>
        <p className="text-sm text-[#94A3B8] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#475569] leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">1. Information We Collect</h2>
            <p>
              We collect information you provide directly (name, email, reviews) and
              data generated through your use of the platform (search queries,
              viewed products, price alerts).
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">2. Shopping Email</h2>
            <p>
              When you create a shopping email forwarding address, purchase confirmation
              emails are processed to extract order data. Email bodies are encrypted
              at rest using AES-256-GCM and are never shared with third parties.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">3. How We Use Your Data</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>Provide personalised price alerts and product recommendations</li>
              <li>Display your purchase history and spending analytics</li>
              <li>Improve DudScore accuracy and fraud detection</li>
              <li>Send transactional notifications (alerts, rewards)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">4. Data Security</h2>
            <p>
              We use industry-standard encryption for data at rest and in transit.
              OAuth tokens and email content are encrypted with separate keys.
              We never store payment card numbers or CVVs.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">5. Cookies</h2>
            <p>
              We use essential cookies for authentication and functional cookies for
              preferences. See our{" "}
              <a href="/cookies" className="text-[#F97316] hover:underline">
                Cookie Policy
              </a>{" "}
              for details.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">6. Your Rights</h2>
            <p>
              You can request data export or account deletion at any time through
              your{" "}
              <a href="/settings" className="text-[#F97316] hover:underline">
                Settings
              </a>{" "}
              page.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">7. Contact</h2>
            <p>
              For privacy-related inquiries, please contact us via our{" "}
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
