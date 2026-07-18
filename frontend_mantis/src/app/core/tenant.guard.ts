import { Injectable, inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot } from '@angular/router';

import { AuthService } from './services/auth.service';

/** Prevents platform administrators from entering company-scoped modules. */
@Injectable({ providedIn: 'root' })
export class TenantGuard implements CanActivate {
  private router = inject(Router);
  private auth = inject(AuthService);

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    void route;
    void state;
    const user = this.auth.currentUserValue;

    if (user && !user.is_superuser && user.company_id) {
      return true;
    }

    this.router.navigate([user?.is_superuser ? '/admin/dashboard' : '/dashboard/default']);
    return false;
  }
}
