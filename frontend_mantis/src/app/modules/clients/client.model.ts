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
}
