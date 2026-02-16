export interface Role {
    id: string;
    name: string;
    description?: string;
    permissions?: { [key: string]: boolean };
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
    role_id?: string;
    role?: Role;
    password?: string; // Only for creation/update
    created_at?: string;
    last_login?: string;
}
