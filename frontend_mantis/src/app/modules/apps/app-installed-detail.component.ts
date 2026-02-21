import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AppInstalledDetail, AppMarketplaceService } from 'src/app/core/services/app-marketplace.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

export interface SchemaField {
  key: string;
  title: string;
  type: string;
  enum?: string[];
  description?: string;
}

@Component({
  selector: 'app-app-installed-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app-installed-detail.component.html',
  styleUrl: './app-installed-detail.component.scss'
})
export class AppInstalledDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private appService = inject(AppMarketplaceService);
  private authService = inject(AuthService);
  private permissionService = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  slug = '';
  appDetail: AppInstalledDetail | null = null;

  // Form
  configForm: Record<string, any> = {};
  schemaFields: SchemaField[] = [];

  // Raw JSON fallback
  configEditor = '{}';
  showRawJson = false;

  ngOnInit(): void {
    if (this.authService.currentUserValue?.is_superuser) {
      this.router.navigate(['/apps/admin']);
      return;
    }

    if (!this.permissionService.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes configurar apps.');
      this.router.navigate(['/dashboard/default']);
      return;
    }

    this.slug = this.route.snapshot.paramMap.get('slug') || '';
    if (!this.slug) {
      this.router.navigate(['/apps/store']);
      return;
    }
    this.loadDetail();
  }

  loadDetail(): void {
    this.loading = true;
    this.appService.getInstalledDetail(this.slug).subscribe({
      next: (data) => {
        this.appDetail = data;
        this.configEditor = JSON.stringify(data.settings || {}, null, 2);

        // Build schemaFields from config_schema
        const schema = (data as any).config_schema;
        this.schemaFields = [];
        if (schema && schema.properties) {
          for (const key of Object.keys(schema.properties)) {
            const prop = schema.properties[key];
            this.schemaFields.push({
              key,
              title: prop.title || key,
              type: prop.type || 'string',
              enum: prop.enum,
              description: prop.description
            });
          }
        }

        // Populate configForm from current settings, fall back to defaults
        const defaults = (data as any).default_config || {};
        const saved = data.settings || {};
        this.configForm = {};
        for (const f of this.schemaFields) {
          this.configForm[f.key] = f.key in saved ? saved[f.key] : (defaults[f.key] ?? '');
        }

        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion de la app.');
        this.router.navigate(['/apps/store']);
      }
    });
  }

  saveConfig(): void {
    this.appService.updateConfig(this.slug, this.configForm).subscribe({
      next: () => {
        this.swal.success('Configuración guardada');
        this.loadDetail();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar la configuracion.');
      }
    });
  }

  saveRawJson(): void {
    try {
      const parsed = JSON.parse(this.configEditor || '{}');
      this.appService.updateConfig(this.slug, parsed).subscribe({
        next: () => {
          this.swal.success('Configuración guardada');
          this.loadDetail();
        },
        error: (err) => {
          this.swal.error('Error', err?.error?.detail || 'No se pudo guardar la configuracion.');
        }
      });
    } catch {
      this.swal.error('JSON inválido', 'Revisa la estructura de configuracion.');
    }
  }

  runDemo(): void {
    if (this.slug !== 'demo-hello') {
      this.swal.warning('Info', 'Esta app no tiene accion demo configurada aun.');
      return;
    }

    this.appService.runDemoHello().subscribe({
      next: (result) => this.swal.success('Debug OK', result.configured_message),
      error: (err) => this.swal.error('Error', err?.error?.detail || 'No se pudo ejecutar la demo.')
    });
  }
}
