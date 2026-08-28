import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  AppInstallEvent,
  AppInstalledDetail,
  AppMarketplaceService,
  BillingSummary,
  TrackingStatus,
  WebhookDelivery
} from 'src/app/core/services/app-marketplace.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

export interface SchemaField {
  key: string;
  title: string;
  type: string;
  enum?: string[];
  description?: string;
  placeholder?: string;
  format?: string;
  required?: boolean;
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
  configForm: Record<string, unknown> = {};
  schemaFields: SchemaField[] = [];

  // Raw JSON fallback
  configEditor = '{}';
  showRawJson = false;
  events: AppInstallEvent[] = [];
  billing: BillingSummary | null = null;
  webhookDeliveries: WebhookDelivery[] = [];
  trackingStatus: TrackingStatus | null = null;

  get appIconClass(): string {
    const icon = (this.appDetail?.icon || 'box').trim();
    return `ti-${icon.replace(/^ti-/, '').replace(/^icon-/, '')}`;
  }

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
        const schema = data.config_schema;
        this.schemaFields = [];
        const properties = schema?.['properties'] as Record<string, Record<string, unknown>> | undefined;
        const requiredFields = Array.isArray(schema?.['required'])
          ? (schema?.['required'] as unknown[]).filter((key): key is string => typeof key === 'string')
          : [];
        if (properties) {
          for (const key of Object.keys(properties)) {
            const prop = properties[key];
            this.schemaFields.push({
              key,
              title: typeof prop['title'] === 'string' ? prop['title'] : key,
              type: typeof prop['type'] === 'string' ? prop['type'] : 'string',
              enum: Array.isArray(prop['enum']) ? prop['enum'].filter((opt): opt is string => typeof opt === 'string') : undefined,
              description: typeof prop['description'] === 'string' ? prop['description'] : undefined,
              placeholder: typeof prop['placeholder'] === 'string' ? prop['placeholder'] : undefined,
              format: typeof prop['format'] === 'string' ? prop['format'] : undefined,
              required: requiredFields.includes(key)
            });
          }
        }

        // Populate configForm from current settings, fall back to defaults
        const defaults = data.default_config || {};
        const saved = data.settings || {};
        this.configForm = {};
        for (const f of this.schemaFields) {
          this.configForm[f.key] = f.key in saved ? saved[f.key] : (defaults[f.key] ?? '');
        }

        this.loading = false;
        this.loadEvents();
        this.loadBilling();
        if (this.supportsWebhooks()) {
          this.loadWebhookDeliveries();
        } else {
          this.webhookDeliveries = [];
        }
        if (this.isTrackingApp()) {
          this.loadTrackingDeliveries();
        } else {
          this.trackingStatus = null;
        }
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion de la app.');
        this.router.navigate(['/apps/store']);
      }
    });
  }

  loadEvents(): void {
    this.appService.getInstalledEvents(this.slug, 20).subscribe({
      next: (events) => {
        this.events = events;
      },
      error: () => {
        this.events = [];
      }
    });
  }

  loadBilling(): void {
    this.appService.getBillingSummary(this.slug).subscribe({
      next: (billing) => {
        this.billing = billing;
      },
      error: () => {
        this.billing = null;
      }
    });
  }

  loadWebhookDeliveries(): void {
    if (!this.supportsWebhooks()) {
      this.webhookDeliveries = [];
      return;
    }
    this.appService.getWebhookDeliveries(this.slug, 25).subscribe({
      next: (deliveries) => {
        this.webhookDeliveries = deliveries;
      },
      error: () => {
        this.webhookDeliveries = [];
      }
    });
  }

  loadTrackingDeliveries(): void {
    if (!this.isTrackingApp()) {
      this.trackingStatus = null;
      return;
    }
    this.appService.getTrackingDeliveries(this.slug, 50).subscribe({
      next: (status) => {
        this.trackingStatus = status;
      },
      error: () => {
        this.trackingStatus = null;
      }
    });
  }

  rotateApiKey(): void {
    this.appService.rotateApiKey(this.slug).subscribe({
      next: (result) => {
        this.swal.success('API key rotada', result.new_api_key);
        this.loadDetail();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo rotar la API key.');
      }
    });
  }

  rotateWebhookSecret(): void {
    if (!this.supportsWebhooks()) return;
    this.appService.rotateWebhookSecret(this.slug).subscribe({
      next: (result) => {
        this.swal.success('Webhook secret rotado', result.webhook_secret);
        this.loadDetail();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo rotar el webhook secret.');
      }
    });
  }

  rotateClientSecret(): void {
    if (!this.supportsExternalApi()) return;
    this.appService.rotateClientSecret(this.slug).subscribe({
      next: (result) => {
        this.swal.success('Client secret rotado', result.new_client_secret);
        this.loadDetail();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo rotar el client secret.');
      }
    });
  }

  testWebhook(): void {
    if (!this.supportsWebhooks()) return;
    this.appService.sendWebhookTest(this.slug).subscribe({
      next: (result) => {
        if (result.delivered) {
          this.swal.success('Webhook enviado', `Status: ${result.status_code || 'ok'}`);
        } else {
          this.swal.warning('Webhook no enviado', result.reason || 'Sin endpoint configurado.');
        }
        this.loadEvents();
        this.loadWebhookDeliveries();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo enviar test webhook.');
      }
    });
  }

  retryWebhook(deliveryId: string): void {
    if (!this.supportsWebhooks()) return;
    this.appService.retryWebhookDelivery(this.slug, deliveryId).subscribe({
      next: (result) => {
        if (result.delivered) {
          this.swal.success('Retry exitoso', `Status: ${result.status_code || 'ok'}`);
        } else {
          this.swal.warning('Retry fallo', result.reason || 'No se pudo entregar.');
        }
        this.loadWebhookDeliveries();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo reintentar webhook.');
      }
    });
  }

  supportsWebhooks(): boolean {
    return !!this.appDetail?.capabilities?.includes('webhook_consumer');
  }

  supportsExternalApi(): boolean {
    return !!this.appDetail?.capabilities?.includes('external_api');
  }

  isTrackingApp(): boolean {
    return ['google-analytics', 'meta-pixel', 'tiktok-pixel'].includes(this.appDetail?.slug || '');
  }

  trackingEventLabel(eventName: string): string {
    const labels: Record<string, string> = {
      page_view: 'Visita de página',
      view_item: 'Producto visto',
      search: 'Búsqueda',
      add_to_cart: 'Añadido al carrito',
      remove_from_cart: 'Quitado del carrito',
      view_cart: 'Carrito visto',
      begin_checkout: 'Inicio de checkout',
      add_shipping_info: 'Datos de envío',
      add_payment_info: 'Datos de pago',
      purchase: 'Compra'
    };
    return labels[eventName] || eventName;
  }

  trackingStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      SENT: 'Entregado',
      RETRY: 'Reintentando',
      FAILED: 'Rechazado',
      NOT_CONFIGURED: 'Pendiente de configuración',
      PENDING: 'Pendiente'
    };
    return labels[status] || status;
  }

  trackingStatusClass(status: string): string {
    const classes: Record<string, string> = {
      SENT: 'bg-success-subtle text-success',
      RETRY: 'bg-warning-subtle text-warning-emphasis',
      FAILED: 'bg-danger-subtle text-danger',
      NOT_CONFIGURED: 'bg-secondary-subtle text-secondary',
      PENDING: 'bg-light text-muted'
    };
    return classes[status] || 'bg-light text-muted';
  }

  saveConfig(): void {
    const missingField = this.schemaFields.find((field) => {
      if (!field.required) return false;
      const value = this.configForm[field.key];
      return value === null || value === undefined || String(value).trim() === '';
    });
    if (missingField) {
      this.swal.warning('Configuración incompleta', `Completa el campo ${missingField.title}.`);
      return;
    }
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

}
