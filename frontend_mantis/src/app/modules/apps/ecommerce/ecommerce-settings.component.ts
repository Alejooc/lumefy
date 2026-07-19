import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

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

@Component({
  selector: 'app-ecommerce-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './ecommerce-settings.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-settings.component.scss']
})
export class EcommerceSettingsComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  domains: StorefrontDomain[] = [];
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

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadStorefronts();
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
    const subdomain = this.storefrontForm.subdomain?.trim();
    if (!subdomain) {
      return 'subdominio.tudominio.com';
    }
    return `${subdomain}.lumefy.shop`;
  }

  createNewStorefront(): void {
    this.selectedStorefrontId = '';
    this.context.setSelectedStorefrontId('');
    this.storefrontForm = this.createStorefrontForm();
    this.brandingForm = this.createBrandingForm();
    this.currencySettingsForm = this.createCurrencySettingsForm();
    this.domainForm = this.createDomainForm();
    this.domains = [];
    this.editingStorefrontId = '';
    this.editingDomainId = '';
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
      slug: this.storefrontForm.slug?.trim(),
      subdomain: this.storefrontForm.subdomain?.trim() || null,
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
      ...this.domainForm,
      storefront_id: this.selectedStorefrontId,
      domain: this.domainForm.domain?.trim()
    };
    const request = this.editingDomainId
      ? this.storefrontService.updateDomain(this.editingDomainId, payload)
      : this.storefrontService.createDomain(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Dominio guardado');
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
    this.domainForm = { ...domain };
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
      slug: '',
      subdomain: '',
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
      language: 'es'
    };
  }

  private createDomainForm(): Partial<StorefrontDomain> {
    return {
      domain: '',
      is_primary: false,
      is_verified: false
    };
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
