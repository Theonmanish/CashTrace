'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AnalysisSession,
  DailyTimelinePoint,
  DeadZone,
  InterventionInput,
  RecommendedAction,
  SimulationResponse,
  fetchAnalysisById,
  fetchBackendHealth,
  fetchDemoAnalysis,
  formatINR,
  getSampleCsvDownloadUrl,
  runSimulation,
  triggerDemoAnalyze,
  uploadAndAnalyzeCsv,
} from '@/lib/api/cashtrace';

type HorizonTab = 'combined' | 'historical' | '7_days' | '14_days' | '30_days';
type LedgerFilter = 'ALL' | 'SETTLED' | 'SCHEDULED' | 'OVERDUE';

const SEVERITY_STYLES: Record<
  DeadZone['severity'],
  { badge: string; border: string; bg: string }
> = {
  CRITICAL: {
    badge: 'bg-red-100 text-red-800 border-red-300',
    border: 'border-red-300',
    bg: 'bg-red-50/70',
  },
  HIGH: {
    badge: 'bg-orange-100 text-orange-800 border-orange-300',
    border: 'border-orange-300',
    bg: 'bg-orange-50/70',
  },
  MEDIUM: {
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    border: 'border-amber-200',
    bg: 'bg-amber-50/60',
  },
  LOW: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    border: 'border-emerald-200',
    bg: 'bg-emerald-50/50',
  },
};

const ROOT_CAUSE_LABELS: Record<string, string> = {
  CUSTOMER_PAYMENT_DELAY: 'Customer Payment Delay',
  SUPPLIER_PAYMENT_CLUSTER: 'Supplier Payment Cluster',
  RECURRING_EXPENSE_SURGE: 'Recurring Expense Surge',
  TIMING_MISMATCH: 'Cash Timing Mismatch',
};

export function CashTraceDashboard() {
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // View controls
  const [horizonTab, setHorizonTab] = useState<HorizonTab>('combined');
  const [ledgerFilter, setLedgerFilter] = useState<LedgerFilter>('ALL');
  const [showUploadPanel, setShowUploadPanel] = useState<boolean>(false);

  // CSV Upload Form state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [openingCashInput, setOpeningCashInput] = useState<string>('220000');
  const [safetyReserveInput, setSafetyReserveInput] = useState<string>('100000');
  const [accountNameInput, setAccountNameInput] = useState<string>(
    'Shree Precision Components Pvt Ltd'
  );
  const [asOfDateInput, setAsOfDateInput] = useState<string>('');
  const [lookupSessionId, setLookupSessionId] = useState<string>('');

  // Custom What-If Simulator Builder state
  const [simScenarioName, setSimScenarioName] = useState<string>(
    'Collect Early + Split Supplier Payout'
  );
  const [selectedInflowId, setSelectedInflowId] = useState<string>('TXN-1006');
  const [inflowDaysEarlier, setInflowDaysEarlier] = useState<string>('8');
  const [enableInflowIntervention, setEnableInflowIntervention] = useState<boolean>(true);

  const [selectedOutflowId, setSelectedOutflowId] = useState<string>('TXN-1010');
  const [outflowMode, setOutflowMode] = useState<'SPLIT' | 'SHIFT'>('SPLIT');
  const [outflowSplitCount, setOutflowSplitCount] = useState<string>('2');
  const [outflowIntervalDays, setOutflowIntervalDays] = useState<string>('12');
  const [enableOutflowIntervention, setEnableOutflowIntervention] = useState<boolean>(true);

  const [enableReserveIntervention, setEnableReserveIntervention] = useState<boolean>(false);
  const [newReserveAmount, setNewReserveAmount] = useState<string>('90000');

  const loadInitialDemo = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const health = await fetchBackendHealth();
      setBackendOnline(health.status === 'ok');
      const demo = await fetchDemoAnalysis();
      setSession(demo);
      setSimulation(null);
      setOpeningCashInput(String(demo.opening_cash));
      setSafetyReserveInput(String(demo.safety_reserve));
      setAccountNameInput(demo.account_name || 'Shree Precision Components Pvt Ltd');
    } catch (err) {
      setBackendOnline(false);
      setError(
        (err as Error).message ||
          'Unable to connect to CashTrace FastAPI backend on http://localhost:8000.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialDemo();
  }, [loadInitialDemo]);

  const handleResetDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const freshDemo = await triggerDemoAnalyze();
      setSession(freshDemo);
      setSimulation(null);
      setBackendOnline(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await uploadAndAnalyzeCsv({
        file: csvFile,
        openingCash: Number(openingCashInput) || 0,
        safetyReserve: Number(safetyReserveInput) || 100000,
        accountName: accountNameInput,
        asOfDate: asOfDateInput || undefined,
      });
      setSession(result);
      setSimulation(null);
      setShowUploadPanel(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadById = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupSessionId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAnalysisById(lookupSessionId.trim());
      setSession(result);
      setSimulation(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunCustomSimulation = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!session) return;

    const interventions: InterventionInput[] = [];
    if (enableInflowIntervention && selectedInflowId) {
      interventions.push({
        type: 'CUSTOMER_PAYMENT_EARLIER',
        transaction_id: selectedInflowId,
        days_earlier: Math.max(1, Number(inflowDaysEarlier) || 5),
      });
    }
    if (enableOutflowIntervention && selectedOutflowId) {
      if (outflowMode === 'SPLIT') {
        interventions.push({
          type: 'SUPPLIER_PAYMENT_SPLIT',
          transaction_id: selectedOutflowId,
          split_count: Math.max(2, Number(outflowSplitCount) || 2),
          split_interval_days: Math.max(1, Number(outflowIntervalDays) || 10),
        });
      } else {
        interventions.push({
          type: 'SUPPLIER_PAYMENT_SHIFTED',
          transaction_id: selectedOutflowId,
          shift_days: Math.max(1, Number(outflowIntervalDays) || 7),
        });
      }
    }
    if (enableReserveIntervention) {
      interventions.push({
        type: 'SAFETY_RESERVE_CHANGED',
        new_safety_reserve: Math.max(0, Number(newReserveAmount) || 90000),
      });
    }

    if (interventions.length === 0) {
      setError('Select at least one What-If intervention to simulate.');
      return;
    }

    setSimulating(true);
    setError(null);
    try {
      const simRes = await runSimulation({
        analysisId: session.analysis_id,
        scenarioName: simScenarioName || 'What-If Mitigation Scenario',
        interventions,
      });
      setSimulation(simRes);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSimulating(false);
    }
  };

  const handleQuickApplyRecommendation = async (rec: RecommendedAction) => {
    if (!session) return;
    setSimulating(true);
    setError(null);
    try {
      const targetId = rec.target_transaction_ids?.[0];
      const interv: InterventionInput =
        rec.action_type === 'CUSTOMER_PAYMENT_EARLIER'
          ? {
              type: 'CUSTOMER_PAYMENT_EARLIER',
              transaction_id: targetId,
              days_earlier: 8,
            }
          : {
              type: 'SUPPLIER_PAYMENT_SPLIT',
              transaction_id: targetId,
              split_count: 2,
              split_interval_days: 12,
            };

      const simRes = await runSimulation({
        analysisId: session.analysis_id,
        scenarioName: rec.title,
        interventions: [interv],
      });
      setSimulation(simRes);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSimulating(false);
    }
  };

  // Timeline series based on selected horizon tab
  const activeTimeline = useMemo<{
    baseline: DailyTimelinePoint[];
    simulated: DailyTimelinePoint[] | null;
    label: string;
  }>(() => {
    if (!session) {
      return { baseline: [], simulated: null, label: '' };
    }
    const histBase = session.timeline || [];
    const f30Base = session.forecasts?.horizons?.['30_days']?.timeline || [];

    const histSim = simulation?.simulated?.reconstruction?.timeline || null;
    const f30Sim =
      simulation?.simulated?.forecasts?.horizons?.['30_days']?.timeline || null;

    if (horizonTab === 'historical') {
      return {
        baseline: histBase,
        simulated: histSim,
        label: `Historical Reconstructed Ledger (${session.reconstruction.start_date} → ${session.as_of_date})`,
      };
    }
    if (horizonTab === '7_days' || horizonTab === '14_days' || horizonTab === '30_days') {
      const hObj = session.forecasts?.horizons?.[horizonTab];
      const simHObj = simulation?.simulated?.forecasts?.horizons?.[horizonTab];
      return {
        baseline: hObj?.timeline || [],
        simulated: simHObj?.timeline || null,
        label: `${horizonTab.replace('_', '-').toUpperCase()} Cash Forecast (${hObj?.start_date} → ${hObj?.end_date})`,
      };
    }
    return {
      baseline: [...histBase, ...f30Base],
      simulated: histSim && f30Sim ? [...histSim, ...f30Sim] : null,
      label: `Combined Historical + 30-Day Forecast (Cutoff: ${session.as_of_date})`,
    };
  }, [session, simulation, horizonTab]);

  // SVG Chart geometry
  const chartGeometry = useMemo(() => {
    const pts = activeTimeline.baseline;
    const simPts = activeTimeline.simulated;
    if (!pts.length || !session) return null;

    const width = 860;
    const height = 250;
    const padX = 48;
    const padY = 24;
    const innerW = width - padX * 2;
    const innerH = height - padY * 2;

    const safetyReserve = simulation
      ? simulation.simulated.safety_reserve
      : session.safety_reserve;

    const allValues = [
      ...pts.map((d) => d.closing_cash),
      ...(simPts ? simPts.map((d) => d.closing_cash) : []),
      safetyReserve,
      0,
    ];
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues, safetyReserve * 1.2);
    const span = Math.max(maxVal - minVal, 1);

    const toX = (idx: number, total: number) =>
      padX + (total <= 1 ? innerW / 2 : (idx / (total - 1)) * innerW);
    const toY = (val: number) => padY + innerH - ((val - minVal) / span) * innerH;

    const baseCoords = pts.map((d, i) => ({
      x: toX(i, pts.length),
      y: toY(d.closing_cash),
      point: d,
    }));

    const basePath = baseCoords
      .map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
      .join(' ');

    const areaPath = `${basePath} L${baseCoords[baseCoords.length - 1].x.toFixed(1)},${(padY + innerH).toFixed(1)} L${baseCoords[0].x.toFixed(1)},${(padY + innerH).toFixed(1)} Z`;

    let simPath = '';
    if (simPts && simPts.length > 0) {
      simPath = simPts
        .map((d, i) => {
          const x = toX(i, simPts.length);
          const y = toY(d.closing_cash);
          return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(' ');
    }

    const reserveY = toY(safetyReserve);

    return {
      width,
      height,
      padX,
      padY,
      innerW,
      innerH,
      minVal,
      maxVal,
      reserveY,
      safetyReserve,
      baseCoords,
      basePath,
      areaPath,
      simPath,
    };
  }, [activeTimeline, session, simulation]);

  const inflowTransactions = useMemo(
    () => (session?.normalized_transactions || []).filter((t) => t.type === 'inflow'),
    [session]
  );

  const outflowTransactions = useMemo(
    () => (session?.normalized_transactions || []).filter((t) => t.type === 'outflow'),
    [session]
  );

  const filteredTransactions = useMemo(() => {
    const list = session?.normalized_transactions || [];
    if (ledgerFilter === 'SETTLED') {
      return list.filter((t) => t.ledger_state === 'SETTLED');
    }
    if (ledgerFilter === 'SCHEDULED') {
      return list.filter((t) => t.ledger_state === 'SCHEDULED');
    }
    if (ledgerFilter === 'OVERDUE') {
      return list.filter((t) => t.is_overdue);
    }
    return list;
  }, [session, ledgerFilter]);

  const allDeadZones = useMemo(() => {
    if (!session) return [];
    const hist = session.dead_zones || [];
    const f30 = session.forecasts?.horizons?.['30_days']?.dead_zones || [];
    return [...hist, ...f30];
  }, [session]);

  return (
    <section
      id="workspace"
      aria-label="CashTrace Live Financial Dead Zone Analyzer"
      className="py-12 border-t border-[#e8ece8] scroll-mt-10"
    >
      {/* Top Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-8 border-b border-[#e8ece8]">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#23845f]">
              Live Engine Connected
            </span>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                backendOnline
                  ? 'bg-emerald-100 text-emerald-800'
                  : backendOnline === false
                  ? 'bg-red-100 text-red-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendOnline
                    ? 'bg-emerald-600'
                    : backendOnline === false
                    ? 'bg-red-600'
                    : 'bg-amber-500 animate-pulse'
                }`}
              />
              {backendOnline
                ? 'FastAPI Backend Online'
                : backendOnline === false
                ? 'Backend Offline (Start port 8000)'
                : 'Connecting...'}
            </span>
            {session?.persistence && (
              <span className="hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-neutral-100 text-neutral-700">
                {session.persistence.supabase_synced
                  ? 'Supabase Synced'
                  : 'In-Memory Store Ready'}
              </span>
            )}
          </div>
          <h2 className="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-[#17241f]">
            {session?.account_name || 'MSME Financial Dead Zone Workspace'}
          </h2>
          {session && (
            <p className="mt-1 text-xs text-[#68756e]">
              Session ID:{' '}
              <code className="px-1.5 py-0.5 rounded bg-neutral-100 text-[#17241f] font-mono">
                {session.analysis_id}
              </code>{' '}
              · As-of Cutoff: <strong>{session.as_of_date}</strong> · Safety Reserve:{' '}
              <strong>{formatINR(session.safety_reserve)}</strong>
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={handleResetDemo}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg border border-[#d5dfd8] bg-white hover:bg-[#f3f7f4] text-xs font-semibold text-[#1d2b24] transition cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Loading...' : '↻ Load MSME Demo'}
          </button>

          <a
            href={getSampleCsvDownloadUrl()}
            download="cashtrace_msme_sample.csv"
            className="px-3.5 py-2 rounded-lg border border-[#d5dfd8] bg-white hover:bg-[#f3f7f4] text-xs font-semibold text-[#1d2b24] transition"
          >
            ↓ Sample CSV
          </a>

          <button
            type="button"
            onClick={() => setShowUploadPanel((prev) => !prev)}
            className="px-4 py-2 rounded-lg bg-[#1f7858] hover:bg-[#195f46] text-white text-xs font-semibold transition cursor-pointer"
          >
            {showUploadPanel ? '✕ Close Upload' : '+ Upload CSV / Analyze'}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          role="alert"
          className="mt-6 p-4 rounded-xl border border-red-300 bg-red-50 text-red-900 text-xs flex items-center justify-between gap-4"
        >
          <div>
            <strong className="font-semibold">Engine Alert: </strong>
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="px-2.5 py-1 rounded bg-red-100 hover:bg-red-200 text-red-800 font-semibold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Collapsible CSV Upload & Session Lookup Panel */}
      {showUploadPanel && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6 p-6 rounded-2xl border border-[#d5dfd8] bg-white shadow-sm">
          <form onSubmit={handleUploadAnalyze} className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#17241f]">
                Analyze Custom MSME Ledger CSV (POST /api/analyze)
              </h3>
              <span className="text-[11px] text-[#68756e]">
                Validates schema, normalizes hybrid ledger & detects dead zones
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-[#34443b] mb-1">
                  Account / Company Name
                </label>
                <input
                  type="text"
                  value={accountNameInput}
                  onChange={(e) => setAccountNameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#d5dfd8] text-xs"
                  placeholder="Shree Precision Components Pvt Ltd"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#34443b] mb-1">
                  CSV Ledger File (required)
                </label>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-1.5 rounded-lg border border-[#d5dfd8] text-xs bg-[#fbfcfa]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#34443b] mb-1">
                  Opening Cash Balance (INR ₹)
                </label>
                <input
                  type="number"
                  required
                  value={openingCashInput}
                  onChange={(e) => setOpeningCashInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#d5dfd8] text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#34443b] mb-1">
                  Safety Cash Reserve (INR ₹)
                </label>
                <input
                  type="number"
                  required
                  value={safetyReserveInput}
                  onChange={(e) => setSafetyReserveInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#d5dfd8] text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#34443b] mb-1">
                  As-Of Date Cutoff (Optional YYYY-MM-DD)
                </label>
                <input
                  type="date"
                  value={asOfDateInput}
                  onChange={(e) => setAsOfDateInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#d5dfd8] text-xs"
                />
              </div>

              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={loading || !csvFile}
                  className="w-full py-2.5 px-4 rounded-lg bg-[#1f7858] hover:bg-[#195f46] text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Running Engine...' : 'Run Full Deterministic Analysis'}
                </button>
              </div>
            </div>
          </form>

          <form
            onSubmit={handleLoadById}
            className="flex flex-col justify-between p-4 rounded-xl bg-[#f6f9f6] border border-[#e3ebe4]"
          >
            <div>
              <h3 className="text-sm font-bold text-[#17241f]">
                Load Saved Session (GET /api/analysis/&#123;id&#125;)
              </h3>
              <p className="mt-1 text-xs text-[#68756e]">
                Retrieve any persisted analysis session by its UUID or pass{' '}
                <code className="px-1 py-0.5 bg-white rounded">demo</code>.
              </p>
              <input
                type="text"
                value={lookupSessionId}
                onChange={(e) => setLookupSessionId(e.target.value)}
                placeholder="e.g. 33333333-3333-3333-3333-333333333333"
                className="mt-3 w-full px-3 py-2 rounded-lg border border-[#d5dfd8] bg-white text-xs font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !lookupSessionId.trim()}
              className="mt-4 w-full py-2 px-4 rounded-lg border border-[#1f7858] text-[#1f7858] hover:bg-[#1f7858] hover:text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
            >
              Fetch Session
            </button>
          </form>
        </div>
      )}

      {session && (
        <>
          {/* 1. Executive KPI Strip */}
          <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Opening Cash</p>
              <p className="mt-1 text-lg font-bold text-[#17241f]">
                {formatINR(session.summary.opening_cash)}
              </p>
              <span className="text-[10px] text-[#68756e]">Starting balance</span>
            </div>

            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Settled Inflows</p>
              <p className="mt-1 text-lg font-bold text-emerald-700">
                +{formatINR(session.summary.total_inflows)}
              </p>
              <span className="text-[10px] text-[#68756e]">
                {session.summary.settled_transactions} settled txns
              </span>
            </div>

            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Settled Outflows</p>
              <p className="mt-1 text-lg font-bold text-rose-700">
                -{formatINR(session.summary.total_outflows)}
              </p>
              <span className="text-[10px] text-[#68756e]">
                {session.summary.overdue_unpaid_transactions} overdue excluded
              </span>
            </div>

            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Final Closing Cash</p>
              <p className="mt-1 text-lg font-bold text-[#17241f]">
                {formatINR(session.summary.final_closing_cash)}
              </p>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700">
                ✓ Invariant Verified
              </span>
            </div>

            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Lowest Historical Cash</p>
              <p
                className={`mt-1 text-lg font-bold ${
                  session.summary.min_closing_cash < session.safety_reserve
                    ? 'text-red-700'
                    : 'text-[#17241f]'
                }`}
              >
                {formatINR(session.summary.min_closing_cash)}
              </p>
              <span className="text-[10px] text-[#68756e]">
                On {session.reconstruction.min_cash_date}
              </span>
            </div>

            <div className="p-4 rounded-xl border border-[#e8ece8] bg-white">
              <p className="text-[11px] font-medium text-[#68756e]">Detected Dead Zones</p>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-lg font-bold text-amber-800">
                  {session.summary.historical_dead_zones_count} Hist
                </span>
                <span className="text-xs text-[#68756e]">/</span>
                <span className="text-lg font-bold text-rose-700">
                  {session.summary.forecast_30d_dead_zones_count} Forecast
                </span>
              </div>
              <span className="text-[10px] text-[#68756e]">
                ≥2 days below {formatINR(session.safety_reserve, true)}
              </span>
            </div>
          </div>

          {/* 2. Interactive Cash Timeline & Horizon Forecast Chart */}
          <div className="mt-8 p-6 rounded-2xl border border-[#e8ece8] bg-white shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#edf0ed]">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#23845f]">
                  Deterministic Reconstruction & Multi-Horizon Forecast
                </span>
                <h3 className="text-base font-bold text-[#17241f]">
                  {activeTimeline.label}
                </h3>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 bg-[#f4f7f4] p-1 rounded-lg">
                {(
                  [
                    { id: 'combined', label: 'Combined (Hist + 30d)' },
                    { id: 'historical', label: 'Historical' },
                    { id: '7_days', label: '7-Day Forecast' },
                    { id: '14_days', label: '14-Day Forecast' },
                    { id: '30_days', label: '30-Day Forecast' },
                  ] as { id: HorizonTab; label: string }[]
                ).map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setHorizonTab(tab.id)}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
                      horizonTab === tab.id
                        ? 'bg-[#1f7858] text-white shadow-xs'
                        : 'text-[#526057] hover:text-[#17241f]'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Horizon Summary Strip when viewing forecasts */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
              {(['7_days', '14_days', '30_days'] as const).map((hKey) => {
                const h = session.forecasts.horizons[hKey];
                return (
                  <div
                    key={hKey}
                    className="p-3 rounded-xl bg-[#fafcfa] border border-[#e8ece8] flex items-center justify-between"
                  >
                    <div>
                      <p className="text-[11px] font-bold uppercase text-[#526057]">
                        {h.horizon_days}-Day Outlook ({h.end_date})
                      </p>
                      <p className="text-xs text-[#68756e] mt-0.5">
                        Min Cash:{' '}
                        <strong
                          className={
                            h.min_projected_cash < session.safety_reserve
                              ? 'text-red-700'
                              : 'text-emerald-700'
                          }
                        >
                          {formatINR(h.min_projected_cash)}
                        </strong>{' '}
                        · End: <strong>{formatINR(h.ending_projected_cash)}</strong>
                      </p>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                        h.dead_zones_count > 0
                          ? 'bg-red-100 text-red-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {h.dead_zones_count} Dead Zone{h.dead_zones_count === 1 ? '' : 's'}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* SVG Cash Curve */}
            {chartGeometry && (
              <div className="mt-6">
                <div className="flex flex-wrap items-center justify-between gap-4 mb-2 text-xs text-[#68756e]">
                  <div className="flex items-center gap-4">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-3 h-0.5 bg-[#23845f] inline-block" />
                      Baseline Closing Cash
                    </span>
                    {simulation && (
                      <span className="inline-flex items-center gap-1.5 font-semibold text-blue-700">
                        <span className="w-3 h-0.5 bg-blue-600 inline-block" />
                        Simulated What-If Cash ({simulation.scenario_name})
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1.5 text-amber-800">
                      <span className="w-3 h-0.5 border-t border-dashed border-amber-600 inline-block" />
                      Safety Reserve ({formatINR(chartGeometry.safetyReserve)})
                    </span>
                  </div>
                  <span>
                    Range: {formatINR(chartGeometry.minVal)} to{' '}
                    {formatINR(chartGeometry.maxVal)}
                  </span>
                </div>

                <div className="w-full overflow-x-auto">
                  <svg
                    viewBox={`0 0 ${chartGeometry.width} ${chartGeometry.height}`}
                    className="w-full h-60 min-w-[600px]"
                    role="img"
                    aria-label="Daily Closing Cash and Safety Reserve Timeline"
                  >
                    <defs>
                      <linearGradient id="cash-area-grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#27A879" stopOpacity="0.24" />
                        <stop offset="100%" stopColor="#27A879" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Safety Reserve Line */}
                    <line
                      x1={chartGeometry.padX}
                      y1={chartGeometry.reserveY}
                      x2={chartGeometry.width - chartGeometry.padX}
                      y2={chartGeometry.reserveY}
                      stroke="#d97706"
                      strokeWidth="1.5"
                      strokeDasharray="6 4"
                    />
                    <text
                      x={chartGeometry.padX + 6}
                      y={Math.max(14, chartGeometry.reserveY - 6)}
                      fill="#b45309"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      Safety Reserve ({formatINR(chartGeometry.safetyReserve, true)})
                    </text>

                    {/* Baseline Area & Line */}
                    <path d={chartGeometry.areaPath} fill="url(#cash-area-grad)" />
                    <path
                      d={chartGeometry.basePath}
                      fill="none"
                      stroke="#23845f"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />

                    {/* Simulated Overlay Line */}
                    {chartGeometry.simPath && (
                      <path
                        d={chartGeometry.simPath}
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2.5"
                        strokeDasharray="5 3"
                        strokeLinecap="round"
                      />
                    )}

                    {/* Highlight points below safety reserve */}
                    {chartGeometry.baseCoords.map((c, idx) =>
                      c.point.below_safety_reserve ? (
                        <circle
                          key={c.point.date + idx}
                          cx={c.x}
                          cy={c.y}
                          r="4"
                          fill="#dc2626"
                          stroke="#fff"
                          strokeWidth="1.5"
                        >
                          <title>
                            {c.point.date}: {formatINR(c.point.closing_cash)} (Below safety
                            reserve)
                          </title>
                        </circle>
                      ) : null
                    )}
                  </svg>
                </div>
              </div>
            )}
          </div>

          {/* 3. Dead Zones & Root Cause Evidence Grid + 4. What-If Scenario Simulator */}
          <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left 7 cols: Dead Zones & Evidence-Backed Root Causes */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#23845f]">
                    Step 4 & 5 · Dead Zone & Root Cause Engine
                  </span>
                  <h3 className="text-lg font-bold text-[#17241f]">
                    Detected Cash Dead Zones & Transaction Evidence ({allDeadZones.length})
                  </h3>
                </div>
              </div>

              {allDeadZones.length === 0 ? (
                <div className="p-6 rounded-xl border border-emerald-200 bg-emerald-50/50 text-emerald-900 text-xs">
                  No historical or 30-day forecasted dead zones detected. Cash remains safely
                  above {formatINR(session.safety_reserve)}.
                </div>
              ) : (
                allDeadZones.map((dz) => {
                  const style = SEVERITY_STYLES[dz.severity] || SEVERITY_STYLES.MEDIUM;
                  return (
                    <article
                      key={dz.dead_zone_id}
                      className={`p-5 rounded-2xl border ${style.border} ${style.bg} space-y-4`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${style.badge}`}
                            >
                              {dz.severity} · Score {dz.severity_score}/100
                            </span>
                            <span className="px-2 py-0.5 rounded bg-white/80 text-[10px] font-mono font-semibold text-[#34443b]">
                              {dz.dead_zone_id} ({dz.is_forecast ? '30d Forecast' : 'Historical'})
                            </span>
                          </div>
                          <h4 className="mt-2 text-base font-bold text-[#17241f]">
                            {dz.start_date} → {dz.end_date} ({dz.duration} consecutive days)
                          </h4>
                        </div>

                        <div className="text-right">
                          <p className="text-[11px] text-[#526057]">Minimum Cash</p>
                          <p className="text-base font-bold text-red-700">
                            {formatINR(dz.minimum_cash)}
                          </p>
                          <p className="text-[10px] text-red-800">
                            Shortfall: {formatINR(dz.absolute_shortfall)} (
                            {dz.shortfall_percentage}%)
                          </p>
                        </div>
                      </div>

                      {/* Root Causes List */}
                      <div className="space-y-2.5">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-[#34443b]">
                          Evidence-Backed Root Causes ({dz.root_causes.length})
                        </p>
                        {dz.root_causes.map((rc, idx) => (
                          <div
                            key={`${dz.dead_zone_id}-rc-${idx}`}
                            className="p-3 rounded-xl bg-white/90 border border-[#e3ebe4] text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-[#1d2b24]">
                                {ROOT_CAUSE_LABELS[rc.category] || rc.category}
                              </span>
                              <span className="font-semibold text-rose-700">
                                Impact: {formatINR(rc.impact_amount)}
                              </span>
                            </div>
                            <p className="text-[#526057] leading-relaxed">{rc.summary}</p>
                            <div className="flex flex-wrap items-center gap-1.5 pt-1">
                              <span className="text-[10px] font-semibold text-[#68756e]">
                                Evidence IDs:
                              </span>
                              {rc.evidence_transaction_ids.map((tid) => (
                                <code
                                  key={tid}
                                  className="px-1.5 py-0.5 rounded bg-[#eef5f0] text-[#1f7858] font-mono text-[10px] font-semibold"
                                >
                                  {tid}
                                </code>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Recommended Mitigations */}
                      {dz.recommended_actions && dz.recommended_actions.length > 0 && (
                        <div className="pt-2 border-t border-black/10 flex flex-wrap items-center justify-between gap-2">
                          <span className="text-[11px] font-semibold text-[#34443b]">
                            Recommended Action:
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {dz.recommended_actions.map((rec, rIdx) => (
                              <button
                                key={rIdx}
                                type="button"
                                disabled={simulating}
                                onClick={() => handleQuickApplyRecommendation(rec)}
                                className="px-3 py-1.5 rounded-lg bg-[#1f7858] hover:bg-[#195f46] text-white text-[11px] font-semibold transition cursor-pointer disabled:opacity-50"
                              >
                                ⚡ Simulate: {rec.title}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })
              )}
            </div>

            {/* Right 5 cols: Non-Mutating What-If Scenario Simulator */}
            <div className="lg:col-span-5">
              <div className="p-6 rounded-2xl border border-[#d5dfd8] bg-white shadow-xs space-y-5 sticky top-6">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#23845f]">
                    Step 7 · Non-Mutating What-If Simulator
                  </span>
                  <h3 className="text-lg font-bold text-[#17241f]">
                    Simulate Capital Interventions
                  </h3>
                  <p className="text-xs text-[#68756e] mt-0.5">
                    Test pulling customer receivables earlier, splitting/deferring supplier
                    outflows, or adjusting safety reserves without mutating baseline records.
                  </p>
                </div>

                <form onSubmit={handleRunCustomSimulation} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#34443b] mb-1">
                      Scenario Name
                    </label>
                    <input
                      type="text"
                      value={simScenarioName}
                      onChange={(e) => setSimScenarioName(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[#d5dfd8] text-xs"
                    />
                  </div>

                  {/* Intervention A: Customer Payment Earlier */}
                  <div className="p-3.5 rounded-xl bg-[#f7faf8] border border-[#e3ebe4] space-y-2.5">
                    <label className="flex items-center gap-2 text-xs font-bold text-[#17241f] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={enableInflowIntervention}
                        onChange={(e) => setEnableInflowIntervention(e.target.checked)}
                      />
                      1. Accelerate Customer Inflow (CUSTOMER_PAYMENT_EARLIER)
                    </label>
                    {enableInflowIntervention && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                        <div className="sm:col-span-2">
                          <label className="block text-[10px] font-semibold text-[#68756e]">
                            Target Inflow Transaction
                          </label>
                          <select
                            value={selectedInflowId}
                            onChange={(e) => setSelectedInflowId(e.target.value)}
                            className="mt-1 w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                          >
                            {inflowTransactions.map((tx) => (
                              <option key={tx.row_id} value={tx.row_id}>
                                {tx.row_id} · {tx.counterparty} ({formatINR(tx.amount)}) [
                                {tx.effective_date}]
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-semibold text-[#68756e]">
                            Days Earlier
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={60}
                            value={inflowDaysEarlier}
                            onChange={(e) => setInflowDaysEarlier(e.target.value)}
                            className="mt-1 w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Intervention B: Supplier Payment Split / Shift */}
                  <div className="p-3.5 rounded-xl bg-[#f7faf8] border border-[#e3ebe4] space-y-2.5">
                    <label className="flex items-center gap-2 text-xs font-bold text-[#17241f] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={enableOutflowIntervention}
                        onChange={(e) => setEnableOutflowIntervention(e.target.checked)}
                      />
                      2. Split or Defer Supplier Outflow
                    </label>
                    {enableOutflowIntervention && (
                      <div className="space-y-2 pt-1">
                        <div>
                          <label className="block text-[10px] font-semibold text-[#68756e]">
                            Target Outflow Transaction
                          </label>
                          <select
                            value={selectedOutflowId}
                            onChange={(e) => setSelectedOutflowId(e.target.value)}
                            className="mt-1 w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                          >
                            {outflowTransactions.map((tx) => (
                              <option key={tx.row_id} value={tx.row_id}>
                                {tx.row_id} · {tx.counterparty} ({formatINR(tx.amount)}) [
                                {tx.effective_date}]
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="block text-[10px] font-semibold text-[#68756e]">
                              Action Mode
                            </label>
                            <select
                              value={outflowMode}
                              onChange={(e) =>
                                setOutflowMode(e.target.value as 'SPLIT' | 'SHIFT')
                              }
                              className="mt-1 w-full px-2 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                            >
                              <option value="SPLIT">Split Installments</option>
                              <option value="SHIFT">Defer / Shift Later</option>
                            </select>
                          </div>

                          {outflowMode === 'SPLIT' && (
                            <div>
                              <label className="block text-[10px] font-semibold text-[#68756e]">
                                Installments
                              </label>
                              <input
                                type="number"
                                min={2}
                                max={6}
                                value={outflowSplitCount}
                                onChange={(e) => setOutflowSplitCount(e.target.value)}
                                className="mt-1 w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                              />
                            </div>
                          )}

                          <div>
                            <label className="block text-[10px] font-semibold text-[#68756e]">
                              {outflowMode === 'SPLIT' ? 'Interval Days' : 'Shift Days'}
                            </label>
                            <input
                              type="number"
                              min={1}
                              max={60}
                              value={outflowIntervalDays}
                              onChange={(e) => setOutflowIntervalDays(e.target.value)}
                              className="mt-1 w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Intervention C: Safety Reserve Change */}
                  <div className="p-3.5 rounded-xl bg-[#f7faf8] border border-[#e3ebe4] space-y-2">
                    <label className="flex items-center gap-2 text-xs font-bold text-[#17241f] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={enableReserveIntervention}
                        onChange={(e) => setEnableReserveIntervention(e.target.checked)}
                      />
                      3. Adjust Safety Reserve Policy (SAFETY_RESERVE_CHANGED)
                    </label>
                    {enableReserveIntervention && (
                      <div className="pt-1">
                        <input
                          type="number"
                          value={newReserveAmount}
                          onChange={(e) => setNewReserveAmount(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded border border-[#d5dfd8] bg-white text-xs"
                          placeholder="New Safety Reserve in INR"
                        />
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="submit"
                      disabled={simulating}
                      className="flex-1 py-2.5 px-4 rounded-lg bg-[#1f7858] hover:bg-[#195f46] text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
                    >
                      {simulating ? 'Simulating...' : '▶ Run What-If Simulation'}
                    </button>
                    {simulation && (
                      <button
                        type="button"
                        onClick={() => setSimulation(null)}
                        className="py-2.5 px-3 rounded-lg border border-[#d5dfd8] text-xs font-semibold text-[#526057] hover:text-[#17241f] cursor-pointer"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </form>

                {/* Simulation Comparison Outcome Card */}
                {simulation && (
                  <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/60 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-blue-900">
                        Simulation Results: {simulation.scenario_name}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                        {simulation.comparison.dead_zones_eliminated} Dead Zone(s) Eliminated
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2.5 text-xs">
                      <div className="p-2.5 rounded-lg bg-white border border-blue-100">
                        <p className="text-[10px] text-[#68756e]">Historical Dead Zones</p>
                        <p className="font-bold text-[#17241f]">
                          {simulation.comparison.baseline_dead_zones_count} →{' '}
                          <span className="text-emerald-700">
                            {simulation.comparison.simulated_dead_zones_count}
                          </span>
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg bg-white border border-blue-100">
                        <p className="text-[10px] text-[#68756e]">30d Forecast Dead Zones</p>
                        <p className="font-bold text-[#17241f]">
                          {simulation.comparison.baseline_forecast_30d_dead_zones_count} →{' '}
                          <span className="text-emerald-700">
                            {simulation.comparison.simulated_forecast_30d_dead_zones_count}
                          </span>
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg bg-white border border-blue-100">
                        <p className="text-[10px] text-[#68756e]">Min Cash Improvement</p>
                        <p className="font-bold text-emerald-700">
                          +{formatINR(simulation.comparison.min_cash_improvement)}
                        </p>
                        <span className="text-[10px] text-[#68756e]">
                          {formatINR(simulation.comparison.baseline_min_cash)} →{' '}
                          {formatINR(simulation.comparison.simulated_min_cash)}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-lg bg-white border border-blue-100">
                        <p className="text-[10px] text-[#68756e]">Max Shortfall Reduction</p>
                        <p className="font-bold text-emerald-700">
                          {formatINR(simulation.comparison.shortfall_reduction)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 5. Normalized Hybrid Ledger Table (Responsive Table Pattern) */}
          <div className="mt-10 p-6 rounded-2xl border border-[#e8ece8] bg-white shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#edf0ed]">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#23845f]">
                  Step 2 · Hybrid Ledger Normalization (SETTLED vs SCHEDULED)
                </span>
                <h3 id="ledger-table-caption" className="text-base font-bold text-[#17241f]">
                  Normalized Transactions ({filteredTransactions.length} of{' '}
                  {session.normalized_transactions.length})
                </h3>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 bg-[#f4f7f4] p-1 rounded-lg">
                {(
                  [
                    { id: 'ALL', label: `All (${session.normalized_transactions.length})` },
                    {
                      id: 'SETTLED',
                      label: `Settled Historical (${session.summary.settled_transactions})`,
                    },
                    {
                      id: 'SCHEDULED',
                      label: `Scheduled Future (${session.summary.scheduled_transactions})`,
                    },
                    {
                      id: 'OVERDUE',
                      label: `Overdue Unpaid (${session.summary.overdue_unpaid_transactions})`,
                    },
                  ] as { id: LedgerFilter; label: string }[]
                ).map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setLedgerFilter(f.id)}
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition cursor-pointer ${
                      ledgerFilter === f.id
                        ? 'bg-[#1f7858] text-white'
                        : 'text-[#526057] hover:text-[#17241f]'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            <div
              tabIndex={0}
              role="region"
              aria-labelledby="ledger-table-caption"
              className="cashtrace-table-wrapper mt-4"
            >
              <table className="cashtrace-ledger-table w-full text-left text-xs">
                <thead>
                  <tr className="bg-[#f4f7f4] text-[#34443b] border-b border-[#e3ebe4]">
                    <th className="py-2.5 px-3 font-semibold">Row ID</th>
                    <th className="py-2.5 px-3 font-semibold">Effective Date</th>
                    <th className="py-2.5 px-3 font-semibold">Counterparty & Category</th>
                    <th className="py-2.5 px-3 font-semibold">Type</th>
                    <th className="py-2.5 px-3 font-semibold">Amount (INR)</th>
                    <th className="py-2.5 px-3 font-semibold">Ledger State</th>
                    <th className="py-2.5 px-3 font-semibold">Due / Actual Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#edf0ed]">
                  {filteredTransactions.map((tx) => (
                    <tr key={tx.row_id} className="hover:bg-[#fafcfa]">
                      <th scope="row" className="py-2.5 px-3 font-mono font-bold text-[#17241f]">
                        {tx.row_id}
                      </th>
                      <td className="py-2.5 px-3 font-medium">{tx.effective_date}</td>
                      <td className="py-2.5 px-3">
                        <strong className="text-[#17241f]">{tx.counterparty}</strong>
                        <span className="block text-[11px] text-[#68756e]">
                          {tx.category} · {tx.description}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            tx.type === 'inflow'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {tx.type}
                        </span>
                      </td>
                      <td
                        className={`py-2.5 px-3 font-bold ${
                          tx.type === 'inflow' ? 'text-emerald-700' : 'text-rose-700'
                        }`}
                      >
                        {tx.type === 'inflow' ? '+' : '-'}
                        {formatINR(tx.amount)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            tx.is_overdue
                              ? 'bg-amber-100 text-amber-900'
                              : tx.ledger_state === 'SETTLED'
                              ? 'bg-emerald-50 text-emerald-800'
                              : 'bg-blue-50 text-blue-800'
                          }`}
                        >
                          {tx.ledger_state}
                          {tx.is_overdue ? ' (Overdue Unpaid)' : ''}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[11px] text-[#68756e]">
                        {tx.due_date ? `Due: ${tx.due_date}` : 'No due date'}
                        {tx.actual_payment_date ? ` · Paid: ${tx.actual_payment_date}` : ''}
                        {tx.delay_days > 0 ? ` (${tx.delay_days}d late)` : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

