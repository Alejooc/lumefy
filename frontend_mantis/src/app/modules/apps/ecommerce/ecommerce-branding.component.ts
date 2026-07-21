import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  Storefront,
  StorefrontAdminService,
  StorefrontBrandingSettings,
  StorefrontFooterLink,
  StorefrontFooterPaymentMethod,
  StorefrontFooterSettings,
  StorefrontHeaderSettings,
  StorefrontPromoBanner,
  StorefrontSocialLinks
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-ecommerce-branding',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-branding.component.html',
  styleUrls: ['./ecommerce-shared.component.scss']
})
export class EcommerceBrandingComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  editing = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  storefront: Storefront | null = null;
  brandingForm: StorefrontBrandingSettings = this.createBrandingForm();
  headerForm: StorefrontHeaderSettings = this.createHeaderForm();
  footerForm: StorefrontFooterSettings = this.createFooterForm();

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar el branding del ecommerce.');
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
        this.applySelectedStorefront();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar el branding.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  openEditor(): void {
    this.editing = true;
  }

  closeEditor(): void {
    if (!this.saving) {
      this.applySelectedStorefront();
      this.editing = false;
    }
  }

  addPromoBanner(): void {
    this.brandingForm = {
      ...this.brandingForm,
      promo_banners: [
        ...(this.brandingForm.promo_banners || []),
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

  addFooterLink(section: 'account_links' | 'quick_links'): void {
    const current = this.footerForm[section] || [];
    this.footerForm = {
      ...this.footerForm,
      [section]: [...current, { label: '', href: '' }]
    };
  }

  removeFooterLink(section: 'account_links' | 'quick_links', index: number): void {
    this.footerForm = {
      ...this.footerForm,
      [section]: (this.footerForm[section] || []).filter((_, currentIndex) => currentIndex !== index)
    };
  }

  addPaymentMethod(): void {
    const current = this.footerForm.payment_methods || [];
    this.footerForm = {
      ...this.footerForm,
      payment_methods: [...current, this.createPaymentMethod()]
    };
  }

  removePaymentMethod(index: number): void {
    this.footerForm = {
      ...this.footerForm,
      payment_methods: (this.footerForm.payment_methods || []).filter((_, currentIndex) => currentIndex !== index)
    };
  }

  removePromoBanner(index: number): void {
    this.brandingForm = {
      ...this.brandingForm,
      promo_banners: (this.brandingForm.promo_banners || []).filter((_, currentIndex) => currentIndex !== index)
    };
  }

  save(): void {
    if (!this.storefront) {
      return;
    }

    this.saving = true;
    const themeSettings = (this.storefront.theme_settings || {}) as Record<string, unknown>;
    this.storefrontService
      .updateStorefront(this.storefront.id, {
        theme_settings: {
          ...themeSettings,
          branding: this.normalizeBrandingPayload(),
          header: this.normalizeHeaderPayload(),
          footer: this.normalizeFooterPayload()
        }
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.editing = false;
          this.swal.success('Branding guardado');
          this.loadStorefronts();
        },
        error: (err) => {
          this.saving = false;
          this.swal.error('Error', err?.error?.detail || 'No se pudo guardar el branding.');
        }
      });
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    const themeSettings = (this.storefront?.theme_settings || {}) as Record<string, unknown>;
    this.brandingForm = this.normalizeBrandingForm(themeSettings['branding']);
    this.headerForm = this.normalizeHeaderForm(themeSettings['header']);
    this.footerForm = this.normalizeFooterForm(themeSettings['footer']);
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

  private createSocialLinks(): StorefrontSocialLinks {
    return {
      facebook: '',
      instagram: '',
      twitter: '',
      linkedin: ''
    };
  }

  private createHeaderForm(): StorefrontHeaderSettings {
    return {
      support_label: '',
      search_placeholder: '',
      account_heading: '',
      guest_account_label: '',
      sign_out_label: '',
      cart_heading: '',
      recently_viewed_label: '',
      wishlist_label: ''
    };
  }

  private createFooterLink(label = '', href = ''): StorefrontFooterLink {
    return { label, href };
  }

  private createPaymentMethod(label = '', iconUrl = '', href = ''): StorefrontFooterPaymentMethod {
    return { label, icon_url: iconUrl, href };
  }

  private createFooterForm(): StorefrontFooterSettings {
    return {
      help_title: '',
      account_title: '',
      quick_links_title: '',
      app_title: '',
      app_description: '',
      app_store_subtitle: '',
      app_store_label: '',
      app_store_url: '',
      play_store_subtitle: '',
      play_store_label: '',
      play_store_url: '',
      payment_title: '',
      show_social_links: false,
      show_app_downloads: false,
      show_payment_methods: false,
      account_links: [],
      quick_links: [],
      payment_methods: []
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

  private normalizeHeaderForm(input: unknown): StorefrontHeaderSettings {
    const settings = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      support_label: String(settings['support_label'] || ''),
      search_placeholder: String(settings['search_placeholder'] || ''),
      account_heading: String(settings['account_heading'] || ''),
      guest_account_label: String(settings['guest_account_label'] || ''),
      sign_out_label: String(settings['sign_out_label'] || ''),
      cart_heading: String(settings['cart_heading'] || ''),
      recently_viewed_label: String(settings['recently_viewed_label'] || ''),
      wishlist_label: String(settings['wishlist_label'] || '')
    };
  }

  private normalizeHeaderPayload(): StorefrontHeaderSettings {
    return {
      support_label: this.normalizeOptionalText(this.headerForm.support_label),
      search_placeholder: this.normalizeOptionalText(this.headerForm.search_placeholder),
      account_heading: this.normalizeOptionalText(this.headerForm.account_heading),
      guest_account_label: this.normalizeOptionalText(this.headerForm.guest_account_label),
      sign_out_label: this.normalizeOptionalText(this.headerForm.sign_out_label),
      cart_heading: this.normalizeOptionalText(this.headerForm.cart_heading),
      recently_viewed_label: this.normalizeOptionalText(this.headerForm.recently_viewed_label),
      wishlist_label: this.normalizeOptionalText(this.headerForm.wishlist_label)
    };
  }

  private normalizeFooterForm(input: unknown): StorefrontFooterSettings {
    const settings = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      help_title: String(settings['help_title'] || ''),
      account_title: String(settings['account_title'] || ''),
      quick_links_title: String(settings['quick_links_title'] || ''),
      app_title: String(settings['app_title'] || ''),
      app_description: String(settings['app_description'] || ''),
      app_store_subtitle: String(settings['app_store_subtitle'] || ''),
      app_store_label: String(settings['app_store_label'] || ''),
      app_store_url: String(settings['app_store_url'] || ''),
      play_store_subtitle: String(settings['play_store_subtitle'] || ''),
      play_store_label: String(settings['play_store_label'] || ''),
      play_store_url: String(settings['play_store_url'] || ''),
      payment_title: String(settings['payment_title'] || ''),
      show_social_links: settings['show_social_links'] === true,
      show_app_downloads: settings['show_app_downloads'] === true,
      show_payment_methods: settings['show_payment_methods'] === true,
      account_links: this.normalizeFooterLinks(settings['account_links']),
      quick_links: this.normalizeFooterLinks(settings['quick_links']),
      payment_methods: this.normalizePaymentMethods(settings['payment_methods'])
    };
  }

  private normalizeFooterPayload(): StorefrontFooterSettings {
    return {
      help_title: this.normalizeOptionalText(this.footerForm.help_title),
      account_title: this.normalizeOptionalText(this.footerForm.account_title),
      quick_links_title: this.normalizeOptionalText(this.footerForm.quick_links_title),
      app_title: this.normalizeOptionalText(this.footerForm.app_title),
      app_description: this.normalizeOptionalText(this.footerForm.app_description),
      app_store_subtitle: this.normalizeOptionalText(this.footerForm.app_store_subtitle),
      app_store_label: this.normalizeOptionalText(this.footerForm.app_store_label),
      app_store_url: this.normalizeOptionalText(this.footerForm.app_store_url),
      play_store_subtitle: this.normalizeOptionalText(this.footerForm.play_store_subtitle),
      play_store_label: this.normalizeOptionalText(this.footerForm.play_store_label),
      play_store_url: this.normalizeOptionalText(this.footerForm.play_store_url),
      payment_title: this.normalizeOptionalText(this.footerForm.payment_title),
      show_social_links: this.footerForm.show_social_links !== false,
      show_app_downloads: this.footerForm.show_app_downloads !== false,
      show_payment_methods: this.footerForm.show_payment_methods !== false,
      account_links: this.normalizeFooterLinksPayload(this.footerForm.account_links),
      quick_links: this.normalizeFooterLinksPayload(this.footerForm.quick_links),
      payment_methods: this.normalizePaymentMethodsPayload(this.footerForm.payment_methods)
    };
  }

  private normalizeFooterLinks(input: unknown): StorefrontFooterLink[] {
    if (!Array.isArray(input)) {
      return [];
    }
    return input
      .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
      .map((item) => ({
        label: String(item['label'] || ''),
        href: String(item['href'] || '')
      }));
  }

  private normalizeFooterLinksPayload(links: StorefrontFooterLink[] | undefined): StorefrontFooterLink[] {
    return (links || [])
      .map((link) => ({
        label: this.normalizeOptionalText(link.label) || '',
        href: this.normalizeOptionalText(link.href)
      }))
      .filter((link) => link.label);
  }

  private normalizePaymentMethods(input: unknown): StorefrontFooterPaymentMethod[] {
    if (!Array.isArray(input)) {
      return [];
    }
    return input
      .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
      .map((item) => ({
        label: String(item['label'] || ''),
        icon_url: String(item['icon_url'] || ''),
        href: String(item['href'] || '')
      }))
      .filter((item) => item.label || item.icon_url);
  }

  private normalizePaymentMethodsPayload(
    methods: StorefrontFooterPaymentMethod[] | undefined
  ): StorefrontFooterPaymentMethod[] {
    return (methods || [])
      .map((method) => ({
        label: this.normalizeOptionalText(method.label) || '',
        icon_url: this.normalizeOptionalText(method.icon_url),
        href: this.normalizeOptionalText(method.href)
      }))
      .filter((method) => method.label || method.icon_url);
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
