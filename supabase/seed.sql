-- ==============================================================================
-- CashTrace - Supabase Demo Seed Data
-- ==============================================================================

-- 1. Create a dummy demo user profile (or replace with your real auth user id)
do $$
declare
    demo_user_id uuid := '00000000-0000-0000-0000-000000000001';
    account_op_id uuid := '11111111-1111-1111-1111-111111111111';
    account_trading_id uuid := '22222222-2222-2222-2222-222222222222';
begin
    -- Insert demo profile (bypassing auth.users constraint for local demo testing)
    insert into public.profiles (id, email, full_name, company_name, base_currency, default_min_cash_buffer)
    values (
        demo_user_id,
        'demo@cashtrace.internal',
        'Demo Trader & CFO',
        'Alpha Capital & Trading Co.',
        'USD',
        10000.00
    )
    on conflict (id) do nothing;

    -- Insert primary operating bank account
    insert into public.accounts (id, user_id, name, account_type, institution_name, currency, current_balance, min_safety_buffer)
    values (
        account_op_id,
        demo_user_id,
        'Primary Operating Account',
        'checking',
        'Silicon Valley Bank',
        'USD',
        42500.00,
        15000.00
    )
    on conflict (id) do nothing;

    -- Insert brokerage margin trading account
    insert into public.accounts (id, user_id, name, account_type, institution_name, currency, current_balance, min_safety_buffer)
    values (
        account_trading_id,
        demo_user_id,
        'Interactive Brokers Margin',
        'trading_margin',
        'Interactive Brokers',
        'USD',
        120000.00,
        30000.00
    )
    on conflict (id) do nothing;

    -- Insert Sample Transactions
    -- Inflow: Client Retainer
    insert into public.transactions (user_id, account_id, amount, transaction_type, category, description, counterparty, transaction_date, status)
    values (
        demo_user_id,
        account_op_id,
        35000.00,
        'inflow',
        'Client Inflow',
        'Monthly advisory fee',
        'Apex Quantitative LLC',
        now() - interval '5 days',
        'completed'
    );

    -- Outflow: Office & Cloud Infra
    insert into public.transactions (user_id, account_id, amount, transaction_type, category, description, counterparty, transaction_date, status)
    values (
        demo_user_id,
        account_op_id,
        -8400.00,
        'outflow',
        'Infrastructure',
        'AWS & Trading API Servers',
        'Amazon Web Services',
        now() - interval '2 days',
        'completed'
    );

    -- Scheduled Outflow: Impending Payroll (Triggers Dead Zone risk)
    insert into public.transactions (user_id, account_id, amount, transaction_type, category, description, counterparty, transaction_date, status)
    values (
        demo_user_id,
        account_op_id,
        -48000.00,
        'outflow',
        'Payroll',
        'Semi-monthly engineering & trading team payroll',
        'Gusto Payroll',
        now() + interval '4 days',
        'scheduled'
    );

    -- Impending Outflow: Options Margin Requirement
    insert into public.transactions (user_id, account_id, amount, transaction_type, category, description, counterparty, transaction_date, status)
    values (
        demo_user_id,
        account_op_id,
        -25000.00,
        'margin_call',
        'Margin Requirement',
        'Transfer to IBKR for index short strangle collateral',
        'Interactive Brokers LLC',
        now() + interval '5 days',
        'scheduled'
    );

    -- Delayed Inflow (Expected later)
    insert into public.transactions (user_id, account_id, amount, transaction_type, category, description, counterparty, transaction_date, status)
    values (
        demo_user_id,
        account_op_id,
        50000.00,
        'inflow',
        'Receivable',
        'Trading Profit Allocation - delayed T+5 settlement',
        'ClearStreet Clearing',
        now() + interval '12 days',
        'forecasted'
    );

    -- Insert Detected "Dead Zone" Event
    insert into public.dead_zone_events (
        user_id,
        account_id,
        title,
        severity,
        status,
        start_date,
        end_date,
        lowest_projected_balance,
        shortfall_amount,
        root_causes,
        recommended_actions,
        detected_at
    )
    values (
        demo_user_id,
        account_op_id,
        'Critical Liquidity Crunch: Payroll & Margin Call Overlap',
        'critical',
        'active',
        (current_date + interval '4 days')::date,
        (current_date + interval '11 days')::date,
        -38900.00,
        53900.00,
        '[
            {"factor": "Payroll disbursement scheduled for Day +4", "impact": -48000},
            {"factor": "Simultaneous broker margin call on Day +5", "impact": -25000},
            {"factor": "Customer settlement delayed to Day +12", "impact": 50000}
        ]'::jsonb,
        '[
            {"action": "Drawdown $40k on revolving credit line before Day +4", "estimated_cost": 250},
            {"action": "Negotiate 5-day payroll deferral or split batch", "feasibility": "Medium"},
            {"action": "Close 30% of high-margin options legs in IBKR to free $18,000 cash", "feasibility": "High"}
        ]'::jsonb,
        now()
    );

    -- Insert Simulation Scenario
    insert into public.scenarios (
        user_id,
        name,
        description,
        baseline_start_date,
        baseline_end_date,
        adjustments,
        projected_dead_zones_count,
        projected_min_balance,
        is_recommended
    )
    values (
        demo_user_id,
        'Mitigation A: Margin Relief + Credit Drawdown',
        'De-risk options positions and draw $25k credit buffer',
        current_date,
        (current_date + interval '30 days')::date,
        '[
            {"type": "reduce_margin_call", "amount": 15000},
            {"type": "short_term_credit_draw", "amount": 25000, "date_offset_days": 3}
        ]'::jsonb,
        0,
        1100.00,
        true
    );

end $$;
