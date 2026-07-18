import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, BroadcastConfig } from 'src/app/modules/admin/admin.service';

@Component({
  selector: 'app-broadcast-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (message && message.is_active) {
      <div
        class="broadcast-banner d-flex justify-content-center align-items-center"
        [ngClass]="getHeaderClass()">
        <div class="content d-flex align-items-center justify-content-center w-100">
          <i class="ti ti-volume-2 me-3 fs-5"></i>
          <span class="message-text">{{ message.message }}</span>
        </div>
      </div>
    }
    `,
  styles: [`
    .broadcast-banner {
      z-index: 1020;
      position: sticky;
      top: 74px; /* Height of the navbar */
      width: 100%;
      padding: 12px 20px;
      border-bottom: 1px solid currentColor;
      margin-bottom: 0;
    }

    .message-text {
      font-weight: 500;
      letter-spacing: normal;
      font-size: 0.95rem;
    }

    .alert-primary { background: var(--bs-primary-bg-subtle); color: var(--bs-primary-text-emphasis); }
    .alert-warning { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .alert-danger { background: var(--bs-danger-bg-subtle); color: var(--bs-danger-text-emphasis); }
    .alert-success { background: var(--bs-success-bg-subtle); color: var(--bs-success-text-emphasis); }
  `]
})
export class BroadcastBannerComponent implements OnInit, OnDestroy {
  private adminService = inject(AdminService);

  message: BroadcastConfig | null = null;
  private intervalId: ReturnType<typeof setInterval> | null = null;

  ngOnInit() {
    this.checkBroadcast();
    // Poll every 60 seconds
    this.intervalId = setInterval(() => this.checkBroadcast(), 60000);
  }

  ngOnDestroy() {
    if (this.intervalId) clearInterval(this.intervalId);
  }

  checkBroadcast() {
    this.adminService.getBroadcast().subscribe({
      next: (data) => this.message = data,
      error: () => { } // Silent fail
    });
  }

  getHeaderClass() {
    switch (this.message?.type) {
      case 'danger': return 'alert-danger';
      case 'warning': return 'alert-warning';
      case 'success': return 'alert-success';
      default: return 'alert-primary';
    }
  }
}
