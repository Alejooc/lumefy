import { Injectable, inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AppMarketplaceService } from './services/app-marketplace.service';
import { PermissionService } from './services/permission.service';

/** Blocks direct URLs to tenant apps that are not enabled for the company. */
@Injectable({ providedIn: 'root' })
export class AppAccessGuard implements CanActivate {
  private readonly apps = inject(AppMarketplaceService);
  private readonly permissions = inject(PermissionService);
  private readonly router = inject(Router);

  canActivate(route: ActivatedRouteSnapshot) {
    const appSlug = route.data['appSlug'] as string | undefined;
    const requiredPermission = route.data['requiredPermission'] as string | undefined;

    if (!appSlug) {
      return true;
    }

    if (requiredPermission && !this.permissions.hasPermission(requiredPermission)) {
      return of(this.unavailable(appSlug));
    }

    return this.apps.getAvailability().pipe(
      map((apps) => apps.some((app) => app.slug === appSlug && app.is_enabled) || this.unavailable(appSlug)),
      catchError(() => of(this.unavailable(appSlug)))
    );
  }

  private unavailable(appSlug: string): UrlTree {
    const destination = this.permissions.hasPermission('manage_company') ? '/apps/store' : '/dashboard/default';
    return this.router.createUrlTree([destination], { queryParams: { unavailable: appSlug } });
  }
}
