import { CommonModule } from '@angular/common';
import Swal from 'sweetalert2';
import { Component, OnInit, inject, ViewChild, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AdminService } from 'src/app/modules/admin/admin.service'; // Use AdminService
import { AuthService } from 'src/app/core/services/auth.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { NgApexchartsModule } from 'ng-apexcharts';
import {
  ChartComponent,
  ApexNonAxisChartSeries,
  ApexPlotOptions,
  ApexChart,
  ApexFill,
  ApexStroke
} from 'ng-apexcharts';

export type ChartOptions = {
  series: ApexNonAxisChartSeries;
  chart: ApexChart;
  labels: string[];
  plotOptions: ApexPlotOptions;
  fill: ApexFill;
  stroke: ApexStroke;
};

@Component({
  selector: 'app-system-health',
  standalone: true,
  imports: [CommonModule, NgApexchartsModule, FormsModule],
  templateUrl: './system-health.component.html',
  styleUrl: './system-health.component.scss'
})
export class SystemHealthComponent implements OnInit {
  private adminService = inject(AdminService);
  private permissionService = inject(PermissionService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef); // Injected

  loading = false;
  errorMessage = '';
  healthData: any = null;
  maintenanceEnabled = false;

  // Broadcast
  broadcastMessage = { message: '', type: 'info', is_active: false };

  // Chart Options
  cpuChartOptions: Partial<ChartOptions>;
  memoryChartOptions: Partial<ChartOptions>;
  diskChartOptions: Partial<ChartOptions>;

  constructor() {
    this.initCharts();
  }

  ngOnInit(): void {
    const canAccess =
      !!this.authService.currentUserValue?.is_superuser ||
      this.permissionService.hasPermission('manage_company');

    if (!canAccess) {
      this.router.navigate(['/dashboard/default']);
      return;
    }

    this.loadHealth();
    this.loadMaintenanceStatus();
    this.loadBroadcast();

    // Auto refresh every 30s
    setInterval(() => {
      if (!this.loading) this.loadHealth();
    }, 30000);
  }

  loadBroadcast() {
    this.adminService.getBroadcast().subscribe(res => {
      this.broadcastMessage = res;
      this.cdr.detectChanges(); // Detect changes
    });
  }

  saveBroadcast() {
    this.loading = true;
    this.adminService.setBroadcast(this.broadcastMessage).subscribe({
      next: () => {
        this.loading = false;
        Swal.fire('Guardado', 'Anuncio global actualizado.', 'success');
        this.cdr.detectChanges(); // Detect changes
      },
      error: () => {
        this.loading = false;
        Swal.fire('Error', 'No se pudo guardar.', 'error');
        this.cdr.detectChanges(); // Detect changes
      }
    });
  }

  loadMaintenanceStatus() {
    this.adminService.getMaintenanceStatus().subscribe(status => {
      this.maintenanceEnabled = status.enabled;
      this.cdr.detectChanges(); // Detect changes
    });
  }

  toggleMaintenance(event: any) {
    const isChecked = event.target.checked;
    // Revert Checkbox state immediately to wait for confirmation
    event.target.checked = !isChecked;

    // Ask for confirmation
    const action = isChecked ? 'ACTIVAR' : 'DESACTIVAR';
    const text = isChecked
      ? 'Esto bloqueará el acceso a todos los usuarios excepto Super Admins.'
      : 'Los usuarios podrán volver a acceder al sistema.';
    const icon = isChecked ? 'warning' : 'info';

    Swal.fire({
      title: `¿${action} Modo Mantenimiento?`,
      text: text,
      icon: icon,
      showCancelButton: true,
      confirmButtonColor: isChecked ? '#d33' : '#3085d6',
      confirmButtonText: `Sí, ${action}`,
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (result.isConfirmed) {
        this.loading = true;
        this.adminService.setMaintenanceStatus(isChecked).subscribe({
          next: (res) => {
            this.maintenanceEnabled = res.enabled;
            this.loading = false;
            // Update Checkbox visually
            event.target.checked = res.enabled;
            this.cdr.detectChanges(); // Detect changes

            Swal.fire(
              'Actualizado',
              `Modo Mantenimiento ${res.enabled ? 'ACTIVADO' : 'DESACTIVADO'}`,
              'success'
            );
          },
          error: () => {
            this.loading = false;
            Swal.fire('Error', 'No se pudo cambiar el estado.', 'error');
            this.cdr.detectChanges(); // Detect changes
          }
        });
      }
    });
  }

  loadHealth(): void {
    this.loading = true;
    this.adminService.getSystemHealth().subscribe({
      next: (data) => {
        this.healthData = data;
        this.updateCharts(data);
        this.loading = false;
        this.cdr.detectChanges(); // Detect changes
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'No se pudo obtener el estado del sistema.';
        this.cdr.detectChanges(); // Detect changes
      }
    });
  }

  updateCharts(data: any) {
    this.cpuChartOptions.series = [data.cpu.percent];
    this.memoryChartOptions.series = [data.memory.percent];
    this.diskChartOptions.series = [data.disk.percent];
  }

  initCharts() {
    const commonOptions: Partial<ChartOptions> = {
      chart: {
        type: 'radialBar',
        height: 250
      },
      plotOptions: {
        radialBar: {
          hollow: {
            size: '70%',
          },
          dataLabels: {
            show: true,
            name: { show: true },
            value: { show: true }
          }
        },
      },
      stroke: {
        lineCap: 'round'
      }
    };

    this.cpuChartOptions = { ...commonOptions, series: [0], labels: ['CPU'] };
    this.memoryChartOptions = { ...commonOptions, series: [0], labels: ['RAM'] };
    this.diskChartOptions = { ...commonOptions, series: [0], labels: ['Disco'] };
  }

  getUptimeString(seconds: number): string {
    const days = Math.floor(seconds / (3600 * 24));
    const hours = Math.floor(seconds % (3600 * 24) / 3600);
    const minutes = Math.floor(seconds % 3600 / 60);
    return `${days}d ${hours}h ${minutes}m`;
  }
}
