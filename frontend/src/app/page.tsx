import { SupabaseStatus } from '@/components/SupabaseStatus';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-12 text-center bg-gradient-to-b from-neutral-50 via-white to-neutral-100 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 text-xs font-medium tracking-wide">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        Hefty-Hacks 2026 • Finance × Trading
      </div>

      <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-neutral-900 dark:text-neutral-50">
        Cash<span className="text-emerald-500">Trace</span>
      </h1>
      <p className="mt-2 text-lg sm:text-xl font-medium text-neutral-600 dark:text-neutral-400">
        Financial Dead Zone Detector
      </p>

      <p className="mt-4 max-w-lg text-sm text-neutral-500 dark:text-neutral-400 leading-relaxed">
        Reconstruct historical liquidity, forecast cash crunches before margin calls hit, and simulate capital interventions.
      </p>

      <SupabaseStatus />
    </main>
  );
}
