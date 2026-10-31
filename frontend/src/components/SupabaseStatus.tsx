'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { fetchBackendSupabaseStatus } from '@/lib/api/cashtrace';

export function SupabaseStatus() {
  const [status, setStatus] = useState<{
    configured: boolean;
    loading: boolean;
    connected?: boolean;
    accountCount?: number;
    backendNote?: string;
    error?: string;
  }>({
    configured: false,
    loading: true,
  });

  useEffect(() => {
    async function checkSupabase() {
      const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

      if (!url || !anonKey || url.includes('your-project-ref')) {
        // Fallback: check if FastAPI backend has Supabase configured or is running in-memory
        try {
          const backendStatus = await fetchBackendSupabaseStatus();
          if (backendStatus.connected) {
            setStatus({
              configured: true,
              loading: false,
              connected: true,
              backendNote: backendStatus.message,
            });
            return;
          }
        } catch {
          // Ignore backend check error here
        }
        setStatus({ configured: false, loading: false });
        return;
      }

      try {
        const supabase = createClient();
        const { count, error } = await supabase
          .from('accounts')
          .select('*', { count: 'exact', head: true });

        if (error) {
          setStatus({
            configured: true,
            loading: false,
            connected: false,
            error: error.message,
          });
        } else {
          setStatus({
            configured: true,
            loading: false,
            connected: true,
            accountCount: count ?? 0,
          });
        }
      } catch (err) {
        setStatus({
          configured: true,
          loading: false,
          connected: false,
          error: (err as Error).message,
        });
      }
    }

    checkSupabase();
  }, []);

  return (
    <div className="mt-8 w-full max-w-md rounded-xl border border-neutral-200 bg-white/70 p-5 shadow-sm backdrop-blur-sm dark:border-neutral-800 dark:bg-neutral-900/60 text-left">
      <div className="flex items-center justify-between pb-3 border-b border-neutral-100 dark:border-neutral-800">
        <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Storage Status
        </span>
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
            status.loading
              ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
              : status.connected
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
              : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              status.loading
                ? 'bg-amber-500 animate-pulse'
                : status.connected
                ? 'bg-emerald-500'
                : 'bg-emerald-500'
            }`}
          />
          {status.loading
            ? 'Checking...'
            : status.connected
            ? 'Supabase Live'
            : status.configured
            ? 'Connection Error'
            : 'In-Memory Active'}
        </span>
      </div>

      <div className="mt-3 text-xs text-neutral-600 dark:text-neutral-400 space-y-1.5">
        {!status.configured ? (
          <p>
            Using FastAPI in-memory store. Add Supabase keys to{' '}
            <code className="rounded bg-neutral-100 px-1 py-0.5 dark:bg-neutral-800">.env.local</code> for cloud persistence.
          </p>
        ) : status.connected ? (
          <p className="text-emerald-600 dark:text-emerald-400">
            {status.backendNote || (
              <>
                Database reachable! Accounts found: <span className="font-semibold">{status.accountCount}</span>.
              </>
            )}
          </p>
        ) : (
          <p className="text-rose-600 dark:text-rose-400">
            Error: {status.error || 'Could not reach Supabase tables.'}
          </p>
        )}
      </div>
    </div>
  );
}
