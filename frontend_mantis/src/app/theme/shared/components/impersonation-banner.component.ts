import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService, User } from 'src/app/core/services/auth.service';

@Component({
  selector: 'app-impersonation-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (active) {
      <div class="impersonation-banner" role="status">
        <div>
          <i class="ti ti-user-shield me-2"></i>
          Sesión delegada activa
          @if (originUser) {
            <span class="text-muted">desde {{ originUser.email }}</span>
          }
        </div>
        <button type="button" class="btn btn-sm btn-outline-primary" [disabled]="returning" (click)="returnToPlatform()">
          <i class="ti ti-arrow-back-up me-1"></i>
          {{ returning ? 'Restaurando...' : 'Volver al panel SaaS' }}
        </button>
      </div>
    }
  `,
  styles: [`
    .impersonation-banner {
      align-items: center;
      background: var(--bs-warning-bg-subtle);
      border-bottom: 1px solid var(--bs-warning-border-subtle);
      color: var(--bs-emphasis-color);
      display: flex;
      font-size: .875rem;
      font-weight: 500;
      gap: 1rem;
      justify-content: space-between;
      padding: .625rem 1.25rem;
    }
  `]
})
export class ImpersonationBannerComponent implements OnInit, OnDestroy {
  private authService = inject(AuthService);
  private router = inject(Router);
  private subscription?: Subscription;

  active = false;
  returning = false;
  originUser: User | null = null;

  ngOnInit(): void {
    this.subscription = this.authService.currentUser.subscribe(() => this.updateState());
    this.updateState();
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  returnToPlatform(): void {
    this.returning = true;
    this.authService.stopImpersonation().subscribe({
      next: (user) => {
        this.returning = false;
        this.updateState();
        if (user?.is_superuser) {
          this.router.navigate(['/admin/dashboard']);
          return;
        }
      },
      error: () => {
        this.returning = false;
      }
    });
  }

  private updateState(): void {
    this.active = this.authService.isImpersonating();
    this.originUser = this.authService.impersonationOriginUser;
  }
}
