import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService } from 'src/app/modules/admin/admin.service';

@Component({
  selector: 'app-broadcast-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="message && message.is_active" 
         class="broadcast-banner d-flex justify-content-center align-items-center"
         [ngClass]="getHeaderClass()">
      <div class="content d-flex align-items-center justify-content-center w-100">
        <i class="feather icon-volume-2 me-3 fs-5"></i> 
        <span class="message-text">{{ message.message }}</span>
      </div>
    </div>
  `,
  styles: [`
    .broadcast-banner {
      z-index: 1020;
      position: sticky;
      top: 74px; /* Height of the navbar */
      width: 100%;
      padding: 12px 20px;
      color: white;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      animation: slideDown 0.5s ease-out;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      margin-bottom: -50px;
    }

    .message-text {
      font-weight: 500;
      letter-spacing: 0.5px;
      font-size: 0.95rem;
    }

    /* Gradients for different types */
    .alert-primary { background: linear-gradient(90deg, #4099ff, #73b4ff); } /* Blue */
    .alert-warning { background: linear-gradient(90deg, #FFB64D, #ffcb80); } /* Orange */
    .alert-danger { background: linear-gradient(90deg, #FF5370, #ff869a); } /* Red */
    .alert-success { background: linear-gradient(90deg, #2ed8b6, #59e0c5); } /* Green */

    @keyframes slideDown {
      from { transform: translateY(-100%); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  `]
})
export class BroadcastBannerComponent implements OnInit, OnDestroy {
  private adminService = inject(AdminService);

  message: any = null;
  private intervalId: any;

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
