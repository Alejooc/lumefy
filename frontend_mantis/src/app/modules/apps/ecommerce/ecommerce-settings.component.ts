import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import {
  Storefront,
  StorefrontAdminService,
  StorefrontBrandingSettings,
  StorefrontCurrencySettings,
  StorefrontDomain,
  StorefrontPromoBanner,
  StorefrontSocialLinks
} from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';
import { ApiService } from 'src/app/core/services/api.service';
import { PriceList, PriceListService } from 'src/app/core/services/pricelist.service';

interface WarehouseOption {
  id: string;
  name: string;
  code: string;
  branch_id: string;
  allows_ecommerce: boolean;
}

@Component({
  selector: 'app-ecommerce-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-settings.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-settings.component.scss']
})
export class EcommerceSettingsComponent implements OnInit, OnDestroy {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);
  private api = inject(ApiService);
  private priceListService = inject(PriceListService);

  loading = false;
  saving = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  domains: StorefrontDomain[] = [];
  warehouses: WarehouseOption[] = [];
  priceLists: PriceList[] = [];
  showDomainsModal = false;
  storefrontForm: Partial<Storefront> = this.createStorefrontForm();
  domainForm: Partial<StorefrontDomain> = this.createDomainForm();
  editingStorefrontId = '';
  editingDomainId = '';
  readonly themeOptions = ['modern', 'minimal', 'retail'];
  readonly currencyOptions = ['USD', 'COP', 'MXN', 'EUR'];
  readonly languageOptions = [
    { value: 'es', label: 'Espanol' },
    { value: 'en', label: 'English' },
    { value: 'pt', label: 'Portugues' }
  ];
  readonly themeLabels: Record<string, string> = {
    modern: 'Modern',
    minimal: 'Minimal',
    retail: 'Retail'
  };
  brandingForm: StorefrontBrandingSettings = this.createBrandingForm();
  currencySettingsForm: StorefrontCurrencySettings = this.createCurrencySettingsForm();
  private domainPollTimer?: number;

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadStorefronts();
    this.priceListService.getPriceLists('SALE').subscribe({
      next: (lists) => this.priceLists = lists.filter((list) => list.active),
      error: () => this.priceLists = []
    });
    this.api.get<WarehouseOption[]>('/warehouses/').subscribe({
      next: (warehouses) => this.warehouses = warehouses.filter((warehouse) => warehouse.allows_ecommerce),
      error: () => this.warehouses = []
    });
  }

  ngOnDestroy(): void {
    this.clearDomainRefresh();
  }

  loadStorefronts(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        const selected = this.storefronts.find((item) => item.id === this.selectedStorefrontId);
        this.storefrontForm = selected ? this.normalizeStorefrontForm({ ...selected }) : this.createStorefrontForm();
        this.editingStorefrontId = selected?.id || '';
        this.loadDomains();
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion de tienda.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    const selected = this.storefronts.find((item) => item.id === this.selectedStorefrontId);
    this.storefrontForm = selected ? this.normalizeStorefrontForm({ ...selected }) : this.createStorefrontForm();
    this.editingStorefrontId = selected?.id || '';
    this.domainForm = this.createDomainForm();
    this.editingDomainId = '';
    this.loadDomains();
  }

  get selectedStorefront(): Storefront | null {
    return this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
  }

  get primaryDomain(): StorefrontDomain | null {
    return this.domains.find((item) => item.is_primary) || this.domains[0] || null;
  }

  get storefrontStatusLabel(): string {
    return this.storefrontForm.is_enabled ? 'Activa' : 'Borrador';
  }

  get storefrontUrlPreview(): string {
    const subdomain = this.storefrontForm.subdomain?.trim() || this.generatedStorefrontSlug;
    return subdomain ? `${subdomain}.${this.platformStorefrontDomain}` : `tu-tienda.${this.platformStorefrontDomain}`;
  }

  get platformStorefrontDomain(): string {
    const host = window.location.hostname.toLowerCase();
    return host.startsWith('panel.') ? host.slice('panel.'.length) : host || 'jaofy.com';
  }

  get generatedStorefrontSlug(): string {
    const value = String(this.storefrontForm.name || '').trim();
    const normalized = value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
    return normalized.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48) || 'tu-tienda';
  }

  loadDomains(): void {
    if (!this.selectedStorefrontId) {
      this.domains = [];
      this.loading = false;
      return;
    }
    this.storefrontService.getDomains(this.selectedStorefrontId).subscribe({
      next: (domains) => {
        this.domains = domains;
        this.loading = false;
        this.scheduleDomainRefresh();
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar los dominios.');
      }
    });
  }

  saveStorefront(): void {
    this.saving = true;
    const normalizedBranding = this.normalizeBrandingPayload();
    const normalizedCurrencySettings = this.normalizeCurrencySettingsPayload();
    const payload = {
      ...this.storefrontForm,
      theme_settings: {
        ...(this.storefrontForm.theme_settings || {}),
        branding: normalizedBranding,
        currency_settings: normalizedCurrencySettings
      }
    };
    const request = this.editingStorefrontId
      ? this.storefrontService.updateStorefront(this.editingStorefrontId, payload)
      : this.storefrontService.createStorefront(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Configuracion guardada');
        this.loadStorefronts();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar la tienda.');
      }
    });
  }

  saveDomain(): void {
    if (!this.selectedStorefrontId) return;
    this.saving = true;
    const payload = {
      storefront_id: this.selectedStorefrontId,
      domain: this.domainForm.domain?.trim(),
      is_primary: !!this.domainForm.is_primary
    };
    const request = this.editingDomainId
      ? this.storefrontService.updateDomain(this.editingDomainId, payload)
      : this.storefrontService.createDomain(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Dominio agregado. Configura y verifica el registro DNS TXT.');
        this.domainForm = this.createDomainForm();
        this.editingDomainId = '';
        this.showDomainsModal = false;
        this.loadDomains();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar el dominio.');
      }
    });
  }

  editDomain(domain: StorefrontDomain): void {
    this.domainForm = { domain: domain.domain, is_primary: domain.is_primary };
    this.editingDomainId = domain.id;
    this.showDomainsModal = true;
  }

  openDomainsModal(): void {
    this.showDomainsModal = true;
  }

  closeDomainsModal(): void {
    this.showDomainsModal = false;
    this.domainForm = this.createDomainForm();
    this.editingDomainId = '';
  }

  async deleteDomain(domain: StorefrontDomain): Promise<void> {
    const confirmed = await this.swal.confirmDelete();
    if (!confirmed) {
      return;
    }

    this.storefrontService.deleteDomain(domain.id).subscribe({
      next: () => {
        this.swal.success('Dominio eliminado');
        if (this.editingDomainId === domain.id) {
          this.domainForm = this.createDomainForm();
          this.editingDomainId = '';
        }
        this.loadDomains();
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo eliminar el dominio.');
      }
    });
  }

  verifyDomain(domain: StorefrontDomain): void {
    this.saving = true;
    this.storefrontService.verifyDomain(domain.id).subscribe({
      next: (verifiedDomain) => {
        this.saving = false;
        const message = verifiedDomain.provisioning_status === 'QUEUED'
          ? 'Dominio verificado. Estamos configurando el proxy y el certificado SSL.'
          : 'Dominio verificado. La automatización de infraestructura requiere configuración.';
        this.swal.success(message);
        this.loadDomains();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Aún no se pudo verificar', err?.error?.detail || 'Revisa el registro TXT y vuelve a intentarlo.');
      }
    });
  }

  retryDomainProvisioning(domain: StorefrontDomain): void {
    this.saving = true;
    this.storefrontService.provisionDomain(domain.id).subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('El dominio volvió a la cola de configuración.');
        this.loadDomains();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('No se pudo reintentar', err?.error?.detail || 'Revisa la configuración DNS y de NPM.');
      }
    });
  }

  domainProvisioningLabel(domain: StorefrontDomain): string {
    const labels: Record<string, string> = {
      PENDING_VERIFICATION: 'Pendiente de verificación',
      QUEUED: 'En cola',
      PROVISIONING: 'Configurando SSL',
      RETRY: 'Reintentando',
      ACTIVE: 'Activo',
      FAILED: 'Requiere atención',
      NOT_CONFIGURED: 'Automatización pendiente',
      REMOVAL_QUEUED: 'Eliminando',
      REMOVING: 'Eliminando',
      REMOVAL_RETRY: 'Reintentando eliminación',
      REMOVAL_FAILED: 'Error al eliminar',
      REMOVED: 'Eliminado'
    };
    return labels[domain.provisioning_status] || domain.provisioning_status || 'Pendiente';
  }

  domainProvisioningClass(domain: StorefrontDomain): string {
    if (domain.provisioning_status === 'ACTIVE') return 'text-bg-success';
    if (['FAILED', 'REMOVAL_FAILED', 'NOT_CONFIGURED'].includes(domain.provisioning_status)) return 'text-bg-danger';
    if (['QUEUED', 'PROVISIONING', 'RETRY', 'REMOVAL_QUEUED', 'REMOVING', 'REMOVAL_RETRY'].includes(domain.provisioning_status)) {
      return 'text-bg-info';
    }
    return 'text-bg-secondary';
  }

  canRetryDomainProvisioning(domain: StorefrontDomain): boolean {
    return domain.is_verified && ['FAILED', 'NOT_CONFIGURED'].includes(domain.provisioning_status);
  }

  themeLabel(themeKey?: string | null): string {
    return this.themeLabels[themeKey || ''] || themeKey || 'Tema';
  }

  addPromoBanner(): void {
    const current = this.brandingForm.promo_banners || [];
    this.brandingForm = {
      ...this.brandingForm,
      promo_banners: [
        ...current,
        {
          id: `promo-${Date.now()}`,
          title: '',
          subtitle: '',
          description: '',
          cta_label: '',
          cta_href: '',
          image_url: '',
          background_color: '',
          accent_color: ''
        }
      ]
    };
  }

  removePromoBanner(index: number): void {
    this.brandingForm = {
      ...this.brandingForm,
      promo_banners: (this.brandingForm.promo_banners || []).filter((_, currentIndex) => currentIndex !== index)
    };
  }

  private createStorefrontForm(): Partial<Storefront> {
    return {
      name: '',
      slug: null,
      subdomain: null,
      is_enabled: false,
      theme_key: 'modern',
      theme_settings: {},
      checkout_settings: {
        allow_guest_checkout: true,
        checkout_mode: 'guest',
        enable_order_notes: true,
        require_phone: false,
        show_delivery_estimate: true,
        flat_shipping_rate: 0,
        free_shipping_threshold: 0
      },
      seo_settings: {
        meta_title: '',
        meta_description: '',
        index_storefront: true
      },
      currency: 'USD',
      language: 'es',
      price_list_id: null
    };
  }

  private createDomainForm(): Partial<StorefrontDomain> {
    return {
      domain: '',
      is_primary: false
    };
  }

  private scheduleDomainRefresh(): void {
    this.clearDomainRefresh();
    const hasImmediateWork = this.domains.some((domain) => ['QUEUED', 'PROVISIONING'].includes(domain.provisioning_status));
    const hasDelayedWork = this.domains.some((domain) => domain.provisioning_status === 'RETRY');
    if (hasImmediateWork || hasDelayedWork) {
      this.domainPollTimer = window.setTimeout(() => this.loadDomains(), hasImmediateWork ? 5000 : 30000);
    }
  }

  private clearDomainRefresh(): void {
    if (this.domainPollTimer !== undefined) {
      window.clearTimeout(this.domainPollTimer);
      this.domainPollTimer = undefined;
    }
  }

  private normalizeStorefrontForm(form: Partial<Storefront>): Partial<Storefront> {
    const themeSettings = (form.theme_settings || {}) as Record<string, unknown>;
    this.brandingForm = this.normalizeBrandingForm(themeSettings['branding']);
    this.currencySettingsForm = this.normalizeCurrencySettingsForm(themeSettings['currency_settings']);
    return form;
  }

  private createBrandingForm(): StorefrontBrandingSettings {
    return {
      logo_url: '',
      support_phone: '',
      support_email: '',
      support_address: '',
      website: '',
      footer_text: '',
      social_links: this.createSocialLinks(),
      promo_banners: []
    };
  }

  private createCurrencySettingsForm(): StorefrontCurrencySettings {
    return {
      show_decimals: false
    };
  }

  private createSocialLinks(): StorefrontSocialLinks {
    return {
      facebook: '',
      instagram: '',
      twitter: '',
      linkedin: ''
    };
  }

  private normalizeBrandingForm(input: unknown): StorefrontBrandingSettings {
    const branding = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    const social = branding['social_links'] && typeof branding['social_links'] === 'object'
      ? (branding['social_links'] as Record<string, unknown>)
      : {};
    const rawPromos = Array.isArray(branding['promo_banners']) ? branding['promo_banners'] : [];

    return {
      logo_url: String(branding['logo_url'] || ''),
      support_phone: String(branding['support_phone'] || ''),
      support_email: String(branding['support_email'] || ''),
      support_address: String(branding['support_address'] || ''),
      website: String(branding['website'] || ''),
      footer_text: String(branding['footer_text'] || ''),
      social_links: {
        facebook: String(social['facebook'] || ''),
        instagram: String(social['instagram'] || ''),
        twitter: String(social['twitter'] || ''),
        linkedin: String(social['linkedin'] || '')
      },
      promo_banners: rawPromos
        .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
        .map((item, index) => ({
          id: String(item['id'] || `promo-${index + 1}`),
          title: String(item['title'] || ''),
          subtitle: String(item['subtitle'] || ''),
          description: String(item['description'] || ''),
          cta_label: String(item['cta_label'] || ''),
          cta_href: String(item['cta_href'] || ''),
          image_url: String(item['image_url'] || ''),
          background_color: String(item['background_color'] || ''),
          accent_color: String(item['accent_color'] || '')
        }))
    };
  }

  private normalizeBrandingPayload(): StorefrontBrandingSettings {
    const socialLinks = this.brandingForm.social_links || this.createSocialLinks();
    const promoBanners = (this.brandingForm.promo_banners || [])
      .map((banner, index) => this.normalizePromoBanner(banner, index))
      .filter((banner): banner is StorefrontPromoBanner => !!banner);

    return {
      logo_url: this.normalizeOptionalText(this.brandingForm.logo_url),
      support_phone: this.normalizeOptionalText(this.brandingForm.support_phone),
      support_email: this.normalizeOptionalText(this.brandingForm.support_email),
      support_address: this.normalizeOptionalText(this.brandingForm.support_address),
      website: this.normalizeOptionalText(this.brandingForm.website),
      footer_text: this.normalizeOptionalText(this.brandingForm.footer_text),
      social_links: {
        facebook: this.normalizeOptionalText(socialLinks.facebook),
        instagram: this.normalizeOptionalText(socialLinks.instagram),
        twitter: this.normalizeOptionalText(socialLinks.twitter),
        linkedin: this.normalizeOptionalText(socialLinks.linkedin)
      },
      promo_banners: promoBanners
    };
  }

  private normalizeCurrencySettingsForm(input: unknown): StorefrontCurrencySettings {
    const settings = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      show_decimals: typeof settings['show_decimals'] === 'boolean' ? (settings['show_decimals'] as boolean) : false
    };
  }

  private normalizeCurrencySettingsPayload(): StorefrontCurrencySettings {
    return {
      show_decimals: this.currencySettingsForm.show_decimals === true
    };
  }

  private normalizePromoBanner(banner: StorefrontPromoBanner, index: number): StorefrontPromoBanner | null {
    const title = this.normalizeOptionalText(banner.title);
    if (!title) {
      return null;
    }
    return {
      id: this.normalizeOptionalText(banner.id) || `promo-${index + 1}`,
      title,
      subtitle: this.normalizeOptionalText(banner.subtitle),
      description: this.normalizeOptionalText(banner.description),
      cta_label: this.normalizeOptionalText(banner.cta_label),
      cta_href: this.normalizeOptionalText(banner.cta_href),
      image_url: this.normalizeOptionalText(banner.image_url),
      background_color: this.normalizeOptionalText(banner.background_color),
      accent_color: this.normalizeOptionalText(banner.accent_color)
    };
  }

  private normalizeOptionalText(value: unknown): string | null {
    const text = String(value || '').trim();
    return text || null;
  }
}
