import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';

@Injectable({
    providedIn: 'root'
})
export class PermissionService {

    constructor(private authService: AuthService) { }

    hasPermission(permission: string): boolean {
        const user = this.authService.currentUserValue;
        if (!user || !user.role || !user.role.permissions) {
            return false;
        }

        // Admin has all permissions? Usually backend handles "all", but frontend might check specific keys.
        // If backend sends "all": true in permissions for admin, check that.
        if (user.role.permissions['all']) {
            return true;
        }

        return !!user.role.permissions[permission];
    }

    hasAnyPermission(permissions: string[]): boolean {
        return permissions.some(p => this.hasPermission(p));
    }
}
