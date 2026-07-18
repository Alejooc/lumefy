import { Injectable, inject } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { PosService } from './services/pos.service';

/** Blocks the POS route unless the company has the POS app enabled and the user can use it. */
@Injectable({ providedIn: 'root' })
export class PosAccessGuard implements CanActivate {
  private router = inject(Router);
  private pos = inject(PosService);

  canActivate() {
    return this.pos.getConfig().pipe(
      map(() => true),
      catchError(() => {
        this.router.navigate(['/apps/store'], { queryParams: { unavailable: 'pos_module' } });
        return of(false);
      })
    );
  }
}
