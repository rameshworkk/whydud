import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Mail, MapPin } from "lucide-react";

export const metadata: Metadata = {
  title: "Contact Us",
  description: "Get in touch with the Whydud team.",
};

export default function ContactPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-2">Contact Us</h1>
        <p className="text-[#64748B] mb-8">
          Have a question, feedback, or business enquiry? We&apos;d love to hear
          from you.
        </p>

        <div className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-lg border border-[#E2E8F0] bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF7ED]">
                <Mail className="h-5 w-5 text-[#F97316]" />
              </div>
              <h2 className="text-lg font-semibold text-[#1E293B]">Email</h2>
            </div>
            <p className="text-sm text-[#64748B]">
              For general queries and support:
            </p>
            <a
              href="mailto:hello@whydud.com"
              className="mt-1 inline-block text-sm font-medium text-[#F97316] hover:underline"
            >
              hello@whydud.com
            </a>
          </div>

          <div className="rounded-lg border border-[#E2E8F0] bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF7ED]">
                <MapPin className="h-5 w-5 text-[#F97316]" />
              </div>
              <h2 className="text-lg font-semibold text-[#1E293B]">Location</h2>
            </div>
            <p className="text-sm text-[#64748B]">
              Whydud Technologies Pvt. Ltd.
              <br />
              India
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
