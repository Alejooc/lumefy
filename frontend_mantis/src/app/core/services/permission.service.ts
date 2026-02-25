import { Injectable, inject } from '@angular/core';
import { AuthService } from './auth.service';

@Injectable({
    providedIn: 'root'
})
export class PermissionService {
    private authService = inject(AuthService);


    hasPermission(permission: string): boolean {
        const user = this.authService.currentUserValue;
        if (!user) return false;

        // Superuser has ALL permissions (including manage_saas)
        if (user.is_superuser) return true;

        // manage_saas is EXCLUSIVELY for superusers — company admins never get it
        if (permission === 'manage_saas') return false;

        if (!user.role || !user.role.permissions) {
            return false;
        }

        // Company admin with "all" gets all COMPANY-level permissions (not SaaS admin)
        if (user.role.permissions['all']) {
            return true;
        }

        return !!user.role.permissions[permission];
    }

    hasAnyPermission(permissions: string[]): boolean {
        return permissions.some(p => this.hasPermission(p));
    }
}
