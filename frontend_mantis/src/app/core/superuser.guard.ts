import { Injectable, inject } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './services/auth.service';

@Injectable({ providedIn: 'root' })
export class SuperuserGuard implements CanActivate {
    private router = inject(Router);
    private authService = inject(AuthService);

    canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
        void route;
        void state;
        const user = this.authService.currentUserValue;

        if (user && user.is_superuser) {
            return true;
        }

        // Non-superuser trying to access admin routes → redirect to company dashboard
        this.router.navigate(['/dashboard/default']);
        return false;
    }
}
