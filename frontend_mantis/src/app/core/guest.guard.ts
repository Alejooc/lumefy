import { Injectable, inject } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './services/auth.service';

@Injectable({ providedIn: 'root' })
export class GuestGuard implements CanActivate {
    router = inject(Router);
    authService = inject(AuthService);

    canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
        void route;
        void state;
        const currentUser = this.authService.currentUserValue;
        if (currentUser) {
            // logged in so redirect to dashboard
            this.router.navigate(['/dashboard/default']);
            return false;
        }

        // not logged in so allow access to login/register
        return true;
    }
}
