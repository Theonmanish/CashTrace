export interface EvidenceItem {
  row_id: string;
  counterparty?: string;
  category?: string;
  description?: string;
  type?: string;
  amount: number;
  due_date?: string | null;
  actual_payment_date?: string | null;
  effective_date?: string;
  ledger_state?: 'SETTLED' | 'SCHEDULED';
  delay_days?: number;
}

export interface RootCause {
  category:
    | 'CUSTOMER_PAYMENT_DELAY'
    | 'SUPPLIER_PAYMENT_CLUSTER'
    | 'RECURRING_EXPENSE_SURGE'
    | 'TIMING_MISMATCH';
  impact_amount: number;
  summary: string;
  evidence_transaction_ids: string[];
  evidence?: EvidenceItem[];
  dead_zone_id?: string;
  is_forecast?: boolean;
}

export interface RecommendedAction {
  action_type:
    | 'CUSTOMER_PAYMENT_EARLIER'
    | 'SUPPLIER_PAYMENT_SHIFTED'
    | 'SUPPLIER_PAYMENT_SPLIT'
    | 'SAFETY_RESERVE_CHANGED';
  title: string;
  expected_impact: number;
  target_transaction_ids: string[];
}

export interface DeadZone {
  dead_zone_id: string;
  start_date: string;
  end_date: string;
  duration: number;
  duration_days: number;
  minimum_cash: number;
  min_cash_date: string;
  safety_reserve: number;
  absolute_shortfall: number;
  shortfall_percentage: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  severity_score: number;
  db_severity: string;
  is_negative_cash: boolean;
  is_forecast: boolean;
  root_causes: RootCause[];
  recommended_actions?: RecommendedAction[];
}

export interface DailyTimelinePoint {
  date: string;
  opening_cash: number;
  inflows: number;
  outflows: number;
  net_movement: number;
  closing_cash: number;
  below_safety_reserve: boolean;
  transaction_ids: string[];
  breakdown?: {
    KNOWN_SCHEDULED: { inflows: number; outflows: number };
    ESTIMATED_RECURRING: { inflows: number; outflows: number };
    ESTIMATED_BASELINE: { inflows: number; outflows: number };
  };
}

export interface NormalizedTransaction {
  row_id: string;
  raw_date: string;
  date: string;
  due_date: string | null;
  actual_payment_date: string | null;
  effective_date: string;
  type: 'inflow' | 'outflow';
  amount: number;
  signed_amount: number;
  category: string;
  counterparty: string;
  description: string;
  ledger_state: 'SETTLED' | 'SCHEDULED';
  is_historical: boolean;
  is_overdue: boolean;
  delay_days: number;
  is_recurring: boolean;
}

export interface ForecastHorizon {
  horizon_days: number;
  start_date: string;
  end_date: string;
  starting_cash: number;
  total_projected_inflows: number;
  total_projected_outflows: number;
  ending_projected_cash: number;
  min_projected_cash: number;
  dead_zones_count: number;
  dead_zones: DeadZone[];
  timeline: DailyTimelinePoint[];
}

export interface AnalysisSummary {
  total_transactions: number;
  settled_transactions: number;
  scheduled_transactions: number;
  overdue_unpaid_transactions: number;
  opening_cash: number;
  total_inflows: number;
  total_outflows: number;
  final_closing_cash: number;
  min_closing_cash: number;
  historical_dead_zones_count: number;
  forecast_30d_dead_zones_count: number;
  invariant_verified: boolean;
}

export interface AnalysisSession {
  analysis_id: string;
  account_name: string;
  as_of_date: string;
  opening_cash: number;
  safety_reserve: number;
  summary: AnalysisSummary;
  normalized_transactions: NormalizedTransaction[];
  reconstruction: {
    as_of_date: string;
    start_date: string;
    end_date: string;
    days_count: number;
    opening_cash: number;
    total_inflows: number;
    total_outflows: number;
    net_cash_flow: number;
    final_closing_cash: number;
    min_closing_cash: number;
    min_cash_date: string;
    max_closing_cash: number;
    safety_reserve: number;
    invariant_verified: boolean;
    timeline: DailyTimelinePoint[];
  };
  timeline: DailyTimelinePoint[];
  dead_zones: DeadZone[];
  root_causes: RootCause[];
  forecasts: {
    as_of_date: string;
    starting_cash: number;
    safety_reserve: number;
    baseline_mode: string;
    degraded_gracefully: boolean;
    scheduled_events_count: number;
    recurring_events_count: number;
    horizons: {
      '7_days': ForecastHorizon;
      '14_days': ForecastHorizon;
      '30_days': ForecastHorizon;
    };
  };
  persistence?: {
    in_memory: boolean;
    supabase_synced: boolean;
    supabase_note: string;
  };
}

export interface InterventionInput {
  type:
    | 'CUSTOMER_PAYMENT_EARLIER'
    | 'SUPPLIER_PAYMENT_SHIFTED'
    | 'SUPPLIER_PAYMENT_SPLIT'
    | 'SAFETY_RESERVE_CHANGED';
  transaction_id?: string;
  transaction_ids?: string[];
  days_earlier?: number;
  shift_days?: number;
  new_date?: string;
  split_count?: number;
  split_interval_days?: number;
  new_safety_reserve?: number;
}

export interface SimulationResponse {
  scenario_id: string;
  analysis_id: string;
  scenario_name: string;
  as_of_date: string;
  applied_interventions: Array<{
    type: string;
    target_ids: string[];
    modified_transaction_ids?: string[];
    previous_safety_reserve?: number;
    new_safety_reserve?: number;
    warning?: string;
  }>;
  comparison: {
    baseline_dead_zones_count: number;
    simulated_dead_zones_count: number;
    baseline_forecast_30d_dead_zones_count: number;
    simulated_forecast_30d_dead_zones_count: number;
    total_dead_zones_delta: number;
    dead_zones_eliminated: number;
    baseline_historical_min_cash: number;
    simulated_historical_min_cash: number;
    historical_min_cash_improvement: number;
    baseline_min_cash: number;
    simulated_min_cash: number;
    min_cash_improvement: number;
    baseline_max_shortfall: number;
    simulated_max_shortfall: number;
    shortfall_reduction: number;
    baseline_safety_reserve: number;
    simulated_safety_reserve: number;
  };
  baseline: {
    safety_reserve: number;
    reconstruction: AnalysisSession['reconstruction'];
    dead_zones: DeadZone[];
    forecasts: AnalysisSession['forecasts'];
  };
  simulated: {
    safety_reserve: number;
    reconstruction: AnalysisSession['reconstruction'];
    dead_zones: DeadZone[];
    forecasts: AnalysisSession['forecasts'];
  };
}

export function getBackendBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, '');
  }
  return 'http://localhost:8000';
}

async function parseApiResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson?.detail) {
        if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail;
        } else if (errJson.detail.message) {
          const errs = Array.isArray(errJson.detail.errors)
            ? ` (${errJson.detail.errors.map((e: { message?: string }) => e.message || JSON.stringify(e)).join('; ')})`
            : '';
          errorDetail = `${errJson.detail.message}${errs}`;
        } else {
          errorDetail = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      // Fallback to status text
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export async function fetchBackendHealth(): Promise<{ status: string }> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(`${baseUrl}/health`, { cache: 'no-store' });
  return parseApiResponse<{ status: string }>(res);
}

export async function fetchBackendSupabaseStatus(): Promise<{
  configured: boolean;
  connected?: boolean;
  message?: string;
  error?: string;
}> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(`${baseUrl}/api/supabase/status`, { cache: 'no-store' });
  return parseApiResponse(res);
}

export async function fetchDemoAnalysis(): Promise<AnalysisSession> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(`${baseUrl}/api/demo`, { cache: 'no-store' });
  return parseApiResponse<AnalysisSession>(res);
}

export async function triggerDemoAnalyze(): Promise<AnalysisSession> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(`${baseUrl}/api/demo/analyze`, {
    method: 'POST',
    cache: 'no-store',
  });
  return parseApiResponse<AnalysisSession>(res);
}

export async function fetchAnalysisById(analysisId: string): Promise<AnalysisSession> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(`${baseUrl}/api/analysis/${encodeURIComponent(analysisId)}`, {
    cache: 'no-store',
  });
  return parseApiResponse<AnalysisSession>(res);
}

export async function uploadAndAnalyzeCsv(params: {
  file?: File | null;
  csvContent?: string;
  openingCash: number;
  safetyReserve: number;
  accountName?: string;
  asOfDate?: string;
}): Promise<AnalysisSession> {
  const baseUrl = getBackendBaseUrl();
  const formData = new FormData();
  formData.append('opening_cash', String(params.openingCash));
  formData.append('safety_reserve', String(params.safetyReserve));
  if (params.accountName?.trim()) {
    formData.append('account_name', params.accountName.trim());
  }
  if (params.asOfDate?.trim()) {
    formData.append('as_of_date', params.asOfDate.trim());
  }
  if (params.file) {
    formData.append('file', params.file);
  } else if (params.csvContent?.trim()) {
    formData.append('csv_content', params.csvContent.trim());
  } else {
    throw new Error('Please select a CSV file or paste CSV transaction rows.');
  }

  const res = await fetch(`${baseUrl}/api/analyze`, {
    method: 'POST',
    body: formData,
  });
  return parseApiResponse<AnalysisSession>(res);
}

export async function runSimulation(params: {
  analysisId: string;
  scenarioName: string;
  interventions: InterventionInput[];
}): Promise<SimulationResponse> {
  const baseUrl = getBackendBaseUrl();
  const res = await fetch(
    `${baseUrl}/api/analysis/${encodeURIComponent(params.analysisId)}/simulate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: params.analysisId,
        scenario_name: params.scenarioName,
        interventions: params.interventions,
      }),
    }
  );
  return parseApiResponse<SimulationResponse>(res);
}

export function getSampleCsvDownloadUrl(): string {
  return `${getBackendBaseUrl()}/api/demo/sample-csv`;
}

export function formatINR(amount: number, compact = false): string {
  const sign = amount < 0 ? '-' : '';
  const abs = Math.abs(amount);
  if (compact) {
    if (abs >= 10000000) {
      return `${sign}₹${(abs / 10000000).toFixed(2)}Cr`;
    }
    if (abs >= 100000) {
      return `${sign}₹${(abs / 100000).toFixed(2)}L`;
    }
    if (abs >= 1000) {
      return `${sign}₹${(abs / 1000).toFixed(1)}k`;
    }
  }
  return `${sign}₹${abs.toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

