export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type AccountType =
  | 'checking'
  | 'savings'
  | 'trading_margin'
  | 'trading_cash'
  | 'brokerage'
  | 'credit_line'
  | 'crypto_wallet';

export type TransactionType =
  | 'inflow'
  | 'outflow'
  | 'transfer'
  | 'trade_settlement'
  | 'margin_call'
  | 'fee_interest';

export type TransactionStatus =
  | 'completed'
  | 'pending'
  | 'scheduled'
  | 'forecasted';

export type DeadZoneSeverity = 'low' | 'warning' | 'critical' | 'fatal';
export type DeadZoneStatus = 'active' | 'monitoring' | 'mitigated' | 'resolved';

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          email: string | null;
          full_name: string | null;
          company_name: string | null;
          base_currency: string;
          default_min_cash_buffer: number;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          email?: string | null;
          full_name?: string | null;
          company_name?: string | null;
          base_currency?: string;
          default_min_cash_buffer?: number;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string | null;
          full_name?: string | null;
          company_name?: string | null;
          base_currency?: string;
          default_min_cash_buffer?: number;
          updated_at?: string;
        };
      };
      accounts: {
        Row: {
          id: string;
          user_id: string;
          name: string;
          account_type: AccountType;
          institution_name: string | null;
          currency: string;
          current_balance: number;
          min_safety_buffer: number;
          is_active: boolean;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          name: string;
          account_type?: AccountType;
          institution_name?: string | null;
          currency?: string;
          current_balance?: number;
          min_safety_buffer?: number;
          is_active?: boolean;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          name?: string;
          account_type?: AccountType;
          institution_name?: string | null;
          currency?: string;
          current_balance?: number;
          min_safety_buffer?: number;
          is_active?: boolean;
          metadata?: Json;
          updated_at?: string;
        };
      };
      transactions: {
        Row: {
          id: string;
          user_id: string;
          account_id: string;
          amount: number;
          transaction_type: TransactionType;
          category: string;
          description: string | null;
          counterparty: string | null;
          transaction_date: string;
          status: TransactionStatus;
          is_recurring: boolean;
          recurrence_rule: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          account_id: string;
          amount: number;
          transaction_type: TransactionType;
          category: string;
          description?: string | null;
          counterparty?: string | null;
          transaction_date: string;
          status?: TransactionStatus;
          is_recurring?: boolean;
          recurrence_rule?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          account_id?: string;
          amount?: number;
          transaction_type?: TransactionType;
          category?: string;
          description?: string | null;
          counterparty?: string | null;
          transaction_date?: string;
          status?: TransactionStatus;
          is_recurring?: boolean;
          recurrence_rule?: string | null;
          metadata?: Json;
          updated_at?: string;
        };
      };
      dead_zone_events: {
        Row: {
          id: string;
          user_id: string;
          account_id: string | null;
          title: string;
          severity: DeadZoneSeverity;
          status: DeadZoneStatus;
          start_date: string;
          end_date: string;
          duration_days: number;
          lowest_projected_balance: number;
          shortfall_amount: number;
          root_causes: Json;
          recommended_actions: Json;
          detected_at: string;
          resolved_at: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          account_id?: string | null;
          title: string;
          severity?: DeadZoneSeverity;
          status?: DeadZoneStatus;
          start_date: string;
          end_date: string;
          lowest_projected_balance: number;
          shortfall_amount?: number;
          root_causes?: Json;
          recommended_actions?: Json;
          detected_at?: string;
          resolved_at?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          title?: string;
          severity?: DeadZoneSeverity;
          status?: DeadZoneStatus;
          start_date?: string;
          end_date?: string;
          lowest_projected_balance?: number;
          shortfall_amount?: number;
          root_causes?: Json;
          recommended_actions?: Json;
          resolved_at?: string | null;
          updated_at?: string;
        };
      };
      scenarios: {
        Row: {
          id: string;
          user_id: string;
          name: string;
          description: string | null;
          baseline_start_date: string;
          baseline_end_date: string;
          adjustments: Json;
          projected_dead_zones_count: number;
          projected_min_balance: number;
          is_recommended: boolean;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          name: string;
          description?: string | null;
          baseline_start_date: string;
          baseline_end_date: string;
          adjustments?: Json;
          projected_dead_zones_count?: number;
          projected_min_balance?: number;
          is_recommended?: boolean;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          name?: string;
          description?: string | null;
          baseline_start_date?: string;
          baseline_end_date?: string;
          adjustments?: Json;
          projected_dead_zones_count?: number;
          projected_min_balance?: number;
          is_recommended?: boolean;
          updated_at?: string;
        };
      };
    };
  };
}
