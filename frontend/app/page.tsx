import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-8 px-6 text-center">
      <span className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
        AI-Powered Sales Intelligence
      </span>
      <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
        Find the right prospects, faster — with evidence your team can trust
      </h1>
      <p className="max-w-2xl text-lg text-slate-600">
        Research public company signals, match them against your products, and generate
        transparent, source-backed sales briefs. Every lead is reviewed and approved by your team
        before any outreach happens.
      </p>
      <div className="flex gap-4">
        <Link
          href="/register"
          className="rounded-md bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Register your organization
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-50"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
