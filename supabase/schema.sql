-- ==============================================================================
-- CashTrace - Supabase Database Schema
-- Financial Dead Zone Detector (Finance x Trading)
-- ==============================================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. ENUMS
-- ------------------------------------------------------------------------------
create type public.account_type as enum (
    'checking',
    'savings',
    'trading_margin',
    'trading_cash',
    'brokerage',
    'credit_line',
    'crypto_wallet'
);

create type public.transaction_type as enum (
    'inflow',             -- Revenue, deposits, funding
    'outflow',            -- Operating expense, vendor payout, payroll
    'transfer',           -- Internal transfer between accounts
    'trade_settlement',   -- Buy/sell settlement cash effect
    'margin_call',        -- Margin deposit required by broker
    'fee_interest'        -- Financing fees, trading commissions, bank fees
);

create type public.transaction_status as enum (
    'completed',
    'pending',
    'scheduled',
    'forecasted'
);

create type public.dead_zone_severity as enum (
    'low',        -- Liquidity dips close to minimum buffer
    'warning',    -- Dips below minimum operating cash reserve
    'critical',   -- Negative cash balance (< $0)
    'fatal'       -- Sustained insolvency / inability to meet margin calls
);

create type public.dead_zone_status as enum (
    'active',
    'monitoring',
    'mitigated',
    'resolved'
);

-- ------------------------------------------------------------------------------
-- 2. USER PROFILES (Linked to Supabase Auth)
-- ------------------------------------------------------------------------------
create table if not exists public.profiles (
    id uuid references auth.users on delete cascade primary key,
    email text,
    full_name text,
    company_name text,
    base_currency text not null default 'USD',
    default_min_cash_buffer numeric(15, 2) not null default 5000.00,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------------------------
-- 3. FINANCIAL ACCOUNTS & TRADING WALLETS
-- ------------------------------------------------------------------------------
create table if not exists public.accounts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    name text not null,
    account_type public.account_type not null default 'checking',
    institution_name text,
    currency text not null default 'USD',
    current_balance numeric(15, 2) not null default 0.00,
    min_safety_buffer numeric(15, 2) not null default 1000.00,
    is_active boolean not null default true,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------------------------
-- 4. TRANSACTIONS & CASH FLOWS
-- ------------------------------------------------------------------------------
create table if not exists public.transactions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    account_id uuid not null references public.accounts(id) on delete cascade,
    amount numeric(15, 2) not null, -- Positive for inflow, negative for outflow
    transaction_type public.transaction_type not null,
    category text not null,          -- e.g. 'Payroll', 'Vendor', 'Options Margin', 'Receivable'
    description text,
    counterparty text,
    transaction_date timestamptz not null,
    status public.transaction_status not null default 'completed',
    is_recurring boolean not null default false,
    recurrence_rule text,            -- e.g. 'RRULE:FREQ=MONTHLY;BYMONTHDAY=1'
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------------------------
-- 5. DAILY BALANCE SNAPSHOTS & RECONSTRUCTION
-- ------------------------------------------------------------------------------
create table if not exists public.balance_snapshots (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    account_id uuid references public.accounts(id) on delete cascade,
    snapshot_date date not null,
    opening_balance numeric(15, 2) not null,
    closing_balance numeric(15, 2) not null,
    total_inflow numeric(15, 2) not null default 0.00,
    total_outflow numeric(15, 2) not null default 0.00,
    is_forecast boolean not null default false,
    confidence_score numeric(4, 3) default 1.000, -- 1.0 for historical, <1.0 for forecast
    created_at timestamptz not null default now(),
    unique(user_id, account_id, snapshot_date, is_forecast)
);

-- ------------------------------------------------------------------------------
-- 6. DEAD ZONE DETECTIONS (The Core CashTrace Engine Output)
-- ------------------------------------------------------------------------------
create table if not exists public.dead_zone_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    account_id uuid references public.accounts(id) on delete set null,
    title text not null,
    severity public.dead_zone_severity not null default 'warning',
    status public.dead_zone_status not null default 'active',
    start_date date not null,
    end_date date not null,
    duration_days integer generated always as ((end_date - start_date) + 1) stored,
    lowest_projected_balance numeric(15, 2) not null,
    shortfall_amount numeric(15, 2) not null default 0.00, -- Amount needed to maintain min buffer
    root_causes jsonb not null default '[]'::jsonb,       -- List of primary contributing outflow spikes / inflow delays
    recommended_actions jsonb not null default '[]'::jsonb, -- Actionable mitigations (delay payment, drawdown line, hedge)
    detected_at timestamptz not null default now(),
    resolved_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------------------------
-- 7. WHAT-IF SIMULATIONS & SCENARIOS
-- ------------------------------------------------------------------------------
create table if not exists public.scenarios (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    name text not null,
    description text,
    baseline_start_date date not null,
    baseline_end_date date not null,
    adjustments jsonb not null default '[]'::jsonb, -- Parameter tweaks: delayed disbursements, new credit lines, sales shifts
    projected_dead_zones_count integer not null default 0,
    projected_min_balance numeric(15, 2) not null default 0.00,
    is_recommended boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------------------------
-- 8. INDEXES FOR HIGH-PERFORMANCE TIME-SERIES QUERIES
-- ------------------------------------------------------------------------------
create index if not exists idx_transactions_user_date on public.transactions(user_id, transaction_date desc);
create index if not exists idx_transactions_account_date on public.transactions(account_id, transaction_date desc);
create index if not exists idx_balance_snapshots_user_date on public.balance_snapshots(user_id, snapshot_date desc);
create index if not exists idx_dead_zone_events_user_status on public.dead_zone_events(user_id, status, severity);
create index if not exists idx_accounts_user_active on public.accounts(user_id, is_active);

-- ------------------------------------------------------------------------------
-- 9. AUTOMATIC TIMESTAMP TRIGGER
-- ------------------------------------------------------------------------------
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated_at
    before update on public.profiles
    for each row execute function public.handle_updated_at();

create trigger trg_accounts_updated_at
    before update on public.accounts
    for each row execute function public.handle_updated_at();

create trigger trg_transactions_updated_at
    before update on public.transactions
    for each row execute function public.handle_updated_at();

create trigger trg_dead_zone_events_updated_at
    before update on public.dead_zone_events
    for each row execute function public.handle_updated_at();

create trigger trg_scenarios_updated_at
    before update on public.scenarios
    for each row execute function public.handle_updated_at();

-- ------------------------------------------------------------------------------
-- 10. AUTH PROFILE CREATION TRIGGER
-- When a user registers with Supabase Auth, automatically create their CashTrace profile.
-- ------------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.profiles (id, email, full_name)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', '')
    )
    on conflict (id) do nothing;
    return new;
end;
$$ language plpgsql security definer;

-- Drop trigger if exists and recreate
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ------------------------------------------------------------------------------
-- 11. ROW LEVEL SECURITY (RLS) POLICIES
-- Each user has strict, isolated access to their own financial data.
-- ------------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.accounts enable row level security;
alter table public.transactions enable row level security;
alter table public.balance_snapshots enable row level security;
alter table public.dead_zone_events enable row level security;
alter table public.scenarios enable row level security;

-- Profiles: Users can view & update their own profile
create policy "Users can view own profile"
    on public.profiles for select
    using (auth.uid() = id);

create policy "Users can update own profile"
    on public.profiles for update
    using (auth.uid() = id);

-- Accounts: Users can CRUD their own accounts
create policy "Users can view own accounts"
    on public.accounts for select
    using (auth.uid() = user_id);

create policy "Users can insert own accounts"
    on public.accounts for insert
    with check (auth.uid() = user_id);

create policy "Users can update own accounts"
    on public.accounts for update
    using (auth.uid() = user_id);

create policy "Users can delete own accounts"
    on public.accounts for delete
    using (auth.uid() = user_id);

-- Transactions: Users can CRUD their own transactions
create policy "Users can view own transactions"
    on public.transactions for select
    using (auth.uid() = user_id);

create policy "Users can insert own transactions"
    on public.transactions for insert
    with check (auth.uid() = user_id);

create policy "Users can update own transactions"
    on public.transactions for update
    using (auth.uid() = user_id);

create policy "Users can delete own transactions"
    on public.transactions for delete
    using (auth.uid() = user_id);

-- Balance Snapshots
create policy "Users can view own balance snapshots"
    on public.balance_snapshots for select
    using (auth.uid() = user_id);

create policy "Users can insert own balance snapshots"
    on public.balance_snapshots for insert
    with check (auth.uid() = user_id);

-- Dead Zone Events
create policy "Users can view own dead zone events"
    on public.dead_zone_events for select
    using (auth.uid() = user_id);

create policy "Users can update own dead zone events"
    on public.dead_zone_events for update
    using (auth.uid() = user_id);

-- Scenarios
create policy "Users can CRUD own scenarios"
    on public.scenarios for all
    using (auth.uid() = user_id);
