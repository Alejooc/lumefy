export interface Client {
    id: string;
    name: string;
    tax_id?: string;
    email?: string;
    phone?: string;
    address?: string;
    notes?: string;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;

    // CRM Fields
    status: string;
    tags?: Record<string, any>;
    credit_limit: number;
    current_balance: number;
    last_interaction_at?: string;
}
