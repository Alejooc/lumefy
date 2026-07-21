import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { StorePaymentGateway, Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type GatewayExtraField = {
  key: string;
  label: string;
  placeholder: string;
  help?: string;
};

@Component({
  selector: 'app-ecommerce-payments',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-payments.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-payments.component.scss']
})
export class EcommercePaymentsComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  accessDenied = false;
  loadError = '';
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  paymentGateways: StorePaymentGateway[] = [];
  readonly gatewayProviders = ['wompi', 'payu', 'mercadopago', 'addi', 'sistecredito', 'whatsapp', 'cod', 'manual_transfer'];
  readonly gatewayMeta: Record<
    string,
    {
      label: string;
      description: string;
      defaultName: string;
      accent: string;
      merchantLabel: string;
      merchantPlaceholder: string;
      publicLabel: string;
      publicPlaceholder: string;
      secretLabel: string;
      secretPlaceholder: string;
    }
  > = {
    wompi: {
      label: 'Wompi',
      description: 'Pasarela local con tarjeta, PSE y medios comunes en Latam.',
      defaultName: 'Wompi',
      accent: 'emerald',
      merchantLabel: 'Merchant ID',
      merchantPlaceholder: 'Public merchant id',
      publicLabel: 'Public key',
      publicPlaceholder: 'Llave publica Wompi',
      secretLabel: 'Integrity / secret',
      secretPlaceholder: 'Llave privada o integrity secret'
    },
    payu: {
      label: 'PayU', description: 'WebCheckout firmado de PayU; usa sandbox sin credenciales para revisar el flujo.',
      defaultName: 'PayU', accent: 'rose', merchantLabel: 'Merchant ID', merchantPlaceholder: 'ID de comercio PayU',
      publicLabel: 'API Login', publicPlaceholder: 'API Login opcional',
      secretLabel: 'API key', secretPlaceholder: 'API key privada PayU'
    },
    mercadopago: {
      label: 'Mercado Pago', description: 'Checkout de Mercado Pago para cobros digitales.',
      defaultName: 'Mercado Pago', accent: 'sky', merchantLabel: 'Collector ID', merchantPlaceholder: 'ID de vendedor',
      publicLabel: 'Public key', publicPlaceholder: 'APP_USR-…',
      secretLabel: 'Access token', secretPlaceholder: 'Token privado de Mercado Pago'
    },
    addi: {
      label: 'Addi', description: 'Crédito Addi nativo: originación, redirección y confirmación automática.',
      defaultName: 'Addi', accent: 'amber', merchantLabel: 'Ally slug', merchantPlaceholder: 'Identificador del aliado (opcional)',
      publicLabel: 'Client ID', publicPlaceholder: 'Client ID Addi',
      secretLabel: 'Client secret', secretPlaceholder: 'Client secret Addi'
    },
    sistecredito: {
      label: 'Sistecrédito', description: 'Checkout hospedado por Sistecrédito; la API nativa se habilita con su contrato técnico.',
      defaultName: 'Sistecrédito', accent: 'indigo', merchantLabel: 'Código de comercio', merchantPlaceholder: 'Código Sistecrédito',
      publicLabel: 'API key', publicPlaceholder: 'Llave pública o API key',
      secretLabel: 'API secret', secretPlaceholder: 'Secreto Sistecrédito'
    },
    whatsapp: {
      label: 'Comprar por WhatsApp', description: 'Envía el carrito y los datos del pedido al WhatsApp comercial configurado.',
      defaultName: 'Comprar por WhatsApp', accent: 'emerald', merchantLabel: 'WhatsApp comercial', merchantPlaceholder: 'Ej. 573001234567',
      publicLabel: 'Etiqueta opcional', publicPlaceholder: 'Ej. Ventas Lumefy',
      secretLabel: 'Secreto', secretPlaceholder: 'No requerido'
    },
    cod: {
      label: 'COD',
      description: 'Pago contra entrega para confirmar el pedido y cobrar al momento de recibirlo.',
      defaultName: 'Pago contra entrega',
      accent: 'amber',
      merchantLabel: 'Referencia interna',
      merchantPlaceholder: 'Codigo interno opcional',
      publicLabel: 'Alias visible',
      publicPlaceholder: 'Ej. Pago contra entrega',
      secretLabel: 'Validacion interna',
      secretPlaceholder: 'Opcional'
    },
    manual_transfer: {
      label: 'Transferencia manual',
      description: 'Pago manual validado por el equipo despues del pedido.',
      defaultName: 'Transferencia bancaria',
      accent: 'slate',
      merchantLabel: 'Referencia interna',
      merchantPlaceholder: 'Codigo o identificador interno',
      publicLabel: 'Alias visible',
      publicPlaceholder: 'Ej. Transferencia bancaria',
      secretLabel: 'Validacion interna',
      secretPlaceholder: 'Opcional'
    }
  };
  readonly providerExtraFields: Record<string, GatewayExtraField[]> = {
    wompi: [
      { key: 'integrity_secret', label: 'Integrity secret', placeholder: 'Secreto de integridad de Wompi' },
      { key: 'events_secret', label: 'Events secret', placeholder: 'Secreto de eventos Wompi', help: 'Protege el webhook de confirmación.' },
      { key: 'redirect_url', label: 'URL retorno', placeholder: 'https://tu-tienda.com/checkout/return' }
    ],
    payu: [
      { key: 'account_id', label: 'Account ID', placeholder: 'Cuenta PayU para Colombia' },
      { key: 'confirmation_url', label: 'URL confirmación', placeholder: 'https://api.tudominio.com/api/v1/storefront/public/payments/payu/webhook/{storefront_id}', help: 'Usa este endpoint público. {storefront_id} se reemplaza automáticamente por la tienda.' }
    ],
    mercadopago: [
      { key: 'notification_url', label: 'URL de notificaciones', placeholder: 'https://api.tudominio.com/api/v1/storefront/public/payments/mercadopago/webhook/{storefront_id}', help: 'Usa este endpoint público. {storefront_id} se reemplaza automáticamente por la tienda.' },
      { key: 'webhook_secret', label: 'Webhook secret', placeholder: 'Secreto de Mercado Pago' }
    ],
    addi: [
      { key: 'callback_url', label: 'URL callback', placeholder: 'https://api.tudominio.com/api/v1/storefront/public/payments/addi/webhook/{storefront_id}', help: 'Addi notificará el resultado del crédito. {storefront_id} se reemplaza automáticamente.' },
      { key: 'callback_username', label: 'Usuario callback', placeholder: 'Usuario de notificación Addi' },
      { key: 'callback_password', label: 'Contraseña callback', placeholder: 'Contraseña de notificación Addi' },
      { key: 'logo_url', label: 'URL de logo', placeholder: 'https://cdn.tudominio.com/logo.png', help: 'Opcional. Se muestra en la experiencia de Addi.' },
      { key: 'audience', label: 'Audience OAuth', placeholder: 'https://api.staging.addi.com', help: 'Opcional: usa el valor entregado por Addi si difiere del predeterminado.' }
    ],
    sistecredito: [
      { key: 'checkout_url', label: 'URL checkout segura', placeholder: 'https://…' },
      { key: 'webhook_secret', label: 'Webhook secret', placeholder: 'Secreto Sistecrédito' }
    ],
    whatsapp: [
      { key: 'whatsapp_number', label: 'Número WhatsApp', placeholder: '573001234567', help: 'Incluye país y número, sin + ni espacios.' },
      { key: 'instructions', label: 'Mensaje al cliente', placeholder: 'Te llevaremos a WhatsApp para confirmar.' }
    ],
    cod: [
      { key: 'instructions', label: 'Instrucciones', placeholder: 'Ej. Paga al recibir tu pedido. Ten el valor exacto disponible.', help: 'Se muestra al finalizar la compra.' }
    ],
    manual_transfer: [
      { key: 'bank_name', label: 'Banco', placeholder: 'Nombre del banco' },
      { key: 'account_holder', label: 'Titular', placeholder: 'Nombre del titular' },
      { key: 'account_number', label: 'Numero de cuenta', placeholder: 'Cuenta bancaria' },
      { key: 'instructions', label: 'Instrucciones', placeholder: 'Texto que vera el cliente al pagar', help: 'Se muestra despues del checkout.' }
    ]
  };
  form: Partial<StorePaymentGateway> = this.createForm();
  editingId = '';
  showEditor = false;

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.accessDenied = true;
      this.loadError = 'Tu usuario no tiene permiso para administrar el ecommerce.';
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.loadError = '';
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.loadGateways();
      },
      error: (err) => {
        this.loading = false;
        this.loadError = err?.error?.detail || 'No se pudieron cargar las tiendas ecommerce.';
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar las pasarelas.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.resetEditor();
    this.loadGateways();
  }

  loadGateways(): void {
    if (!this.selectedStorefrontId) {
      this.paymentGateways = [];
      this.loading = false;
      return;
    }
    this.loading = true;
    this.loadError = '';
    this.storefrontService.getPaymentGateways(this.selectedStorefrontId).subscribe({
      next: (gateways) => {
        this.paymentGateways = gateways;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.loadError = err?.error?.detail || 'No se pudieron cargar las pasarelas.';
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar las pasarelas.');
      }
    });
  }

  save(): void {
    if (!this.selectedStorefrontId) return;
    this.saving = true;
    const payload = {
      ...this.form,
      storefront_id: this.selectedStorefrontId,
      provider: this.form.provider?.trim(),
      display_name: this.form.display_name?.trim(),
      merchant_id: this.form.merchant_id?.trim() || null,
      public_key: this.form.public_key?.trim() || null,
      secret_key_encrypted: this.form.secret_key_encrypted?.trim() || null
    };
    const request = this.editingId
      ? this.storefrontService.updatePaymentGateway(this.editingId, payload)
      : this.storefrontService.createPaymentGateway(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Pasarela guardada');
        this.resetEditor();
        this.loadGateways();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar la pasarela.');
      }
    });
  }

  edit(item: StorePaymentGateway): void {
    this.editingId = item.id;
    this.form = {
      ...item,
      extra_config: { ...(item.extra_config || {}) }
    };
    this.showEditor = true;
  }

  createGateway(provider?: string): void {
    this.form = this.createForm(provider || 'manual_transfer');
    this.editingId = '';
    this.showEditor = true;
  }

  closeEditor(): void {
    this.resetEditor();
  }

  applyProviderPreset(): void {
    const meta = this.gatewayMeta[this.form.provider || 'manual_transfer'];
    if (!this.editingId) {
      this.form.display_name = meta.defaultName;
    }
    this.form.extra_config = this.pruneExtraConfig(this.form.provider || 'manual_transfer', this.form.extra_config);
  }

  providerLabel(provider?: string | null): string {
    return this.gatewayMeta[provider || '']?.label || provider || 'Proveedor';
  }

  providerDescription(provider?: string | null): string {
    return this.gatewayMeta[provider || '']?.description || 'Configuracion de proveedor de pago.';
  }

  providerTone(provider?: string | null): string {
    const accent = this.gatewayMeta[provider || '']?.accent;
    if (accent === 'emerald') return 'teal';
    if (accent === 'amber') return 'amber';
    if (accent === 'rose') return 'indigo';
    if (accent === 'slate') return 'indigo';
    return 'indigo';
  }

  configuredGateway(provider: string): StorePaymentGateway | null {
    return this.paymentGateways.find((item) => item.provider === provider) || null;
  }

  get enabledGatewaysCount(): number {
    return this.paymentGateways.filter((item) => item.is_enabled).length;
  }

  get sandboxGatewaysCount(): number {
    return this.paymentGateways.filter((item) => item.is_sandbox).length;
  }

  get productionGatewaysCount(): number {
    return this.paymentGateways.filter((item) => !item.is_sandbox).length;
  }

  get manualGatewaysCount(): number {
    return this.paymentGateways.filter((item) => item.provider === 'manual_transfer').length;
  }

  get activeStorefront(): Storefront | null {
    return this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
  }

  get providerFields(): GatewayExtraField[] {
    return this.providerExtraFields[this.form.provider || 'manual_transfer'] || [];
  }

  merchantLabel(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.merchantLabel || 'Merchant ID';
  }

  merchantPlaceholder(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.merchantPlaceholder || 'Identificador de comercio';
  }

  publicLabel(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.publicLabel || 'Public key';
  }

  publicPlaceholder(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.publicPlaceholder || 'Llave publica';
  }

  secretLabel(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.secretLabel || 'Secret';
  }

  secretPlaceholder(provider?: string | null): string {
    return this.gatewayMeta[provider || 'manual_transfer']?.secretPlaceholder || 'Token o secreto';
  }

  extraFieldValue(key: string): string {
    const config = (this.form.extra_config ||= {});
    const value = config[key];
    return typeof value === 'string' ? value : '';
  }

  setExtraFieldValue(key: string, value: string): void {
    const config = (this.form.extra_config ||= {});
    config[key] = value;
  }

  openGatewayCard(provider: string): void {
    const configured = this.configuredGateway(provider);
    if (configured) {
      this.edit(configured);
      return;
    }
    this.createGateway(provider);
  }

  private resetEditor(): void {
    this.form = this.createForm();
    this.editingId = '';
    this.showEditor = false;
  }

  private createForm(provider = 'manual_transfer'): Partial<StorePaymentGateway> {
    const meta = this.gatewayMeta[provider];
    return {
      provider,
      display_name: meta.defaultName,
      is_enabled: true,
      is_sandbox: true,
      public_key: '',
      secret_key_encrypted: '',
      merchant_id: '',
      extra_config: this.pruneExtraConfig(provider, {}),
      sort_order: 0
    };
  }

  private pruneExtraConfig(provider: string, config: Record<string, unknown> | undefined): Record<string, unknown> {
    const next: Record<string, unknown> = {};
    const allowedKeys = new Set((this.providerExtraFields[provider] || []).map((field) => field.key));
    for (const [key, value] of Object.entries(config || {})) {
      if (allowedKeys.has(key) && value !== null && value !== undefined && `${value}`.trim() !== '') {
        next[key] = value;
      }
    }
    return next;
  }
}
