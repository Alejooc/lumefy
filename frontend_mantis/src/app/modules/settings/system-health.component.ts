import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { DashboardHealth, DashboardService } from 'src/app/core/services/dashboard.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { PermissionService } from 'src/app/core/services/permission.service';

@Component({
  selector: 'app-system-health',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-health.component.html',
  styleUrl: './system-health.component.scss'
})
export class SystemHealthComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private permissionService = inject(PermissionService);
  private authService = inject(AuthService);
  private router = inject(Router);

  loading = false;
  errorMessage = '';
  healthStatus: DashboardHealth | null = null;

  ngOnInit(): void {
    const canAccess =
      !!this.authService.currentUserValue?.is_superuser ||
      this.permissionService.hasPermission('manage_company');

    if (!canAccess) {
      this.router.navigate(['/dashboard/default']);
      return;
    }

    this.loadHealth();
  }

  loadHealth(): void {
    this.loading = true;
    this.errorMessage = '';

    this.dashboardService.getHealth().subscribe({
      next: (health) => {
        this.healthStatus = health;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'No se pudo validar el estado del sistema.';
      }
    });
  }
}
