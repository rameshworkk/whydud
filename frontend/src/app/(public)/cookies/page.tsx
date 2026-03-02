import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: "How Whydud uses cookies and similar technologies.",
};

export default function CookiePolicyPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-2">Cookie Policy</h1>
        <p className="text-sm text-[#94A3B8] mb-8">Last updated: February 2026</p>

        <div className="space-y-6 text-[#475569] leading-relaxed">
          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">What are cookies?</h2>
            <p>
              Cookies are small text files stored on your device when you visit a
              website. They help us provide a better experience by remembering your
              preferences and login state.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">Cookies we use</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-[#E2E8F0]">
                    <th className="text-left py-2 pr-4 font-semibold text-[#1E293B]">Cookie</th>
                    <th className="text-left py-2 pr-4 font-semibold text-[#1E293B]">Purpose</th>
                    <th className="text-left py-2 font-semibold text-[#1E293B]">Duration</th>
                  </tr>
                </thead>
                <tbody className="text-[#475569]">
                  <tr className="border-b border-[#F1F5F9]">
                    <td className="py-2 pr-4 font-mono text-xs">whydud_auth</td>
                    <td className="py-2 pr-4">Authentication flag for protected pages</td>
                    <td className="py-2">Session</td>
                  </tr>
                  <tr className="border-b border-[#F1F5F9]">
                    <td className="py-2 pr-4 font-mono text-xs">csrftoken</td>
                    <td className="py-2 pr-4">CSRF protection for form submissions</td>
                    <td className="py-2">1 year</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[#1E293B] mb-2">Managing cookies</h2>
            <p>
              You can control cookies through your browser settings. Note that
              disabling essential cookies may prevent you from logging in or using
              certain features.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
