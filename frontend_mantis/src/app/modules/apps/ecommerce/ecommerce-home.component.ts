import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  Storefront,
  StorefrontAdminService,
  StorefrontHomeCategoryCard,
  StorefrontHomeCountdownSettings,
  StorefrontHomeFeatureItem,
  StorefrontHomeHeroPromo,
  StorefrontHomeHeroSlide,
  StorefrontHomeNewsletterSettings,
  StorefrontHomeSectionCopy,
  StorefrontHomeSettings,
  StorefrontHomeTestimonialsSettings,
  StorefrontPromoBanner
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-ecommerce-home',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-home.component.html',
  styleUrls: ['./ecommerce-shared.component.scss']
})
export class EcommerceHomeComponent implements OnInit {
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
  form: StorefrontHomeSettings = this.createForm();

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar el home del ecommerce.');
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
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuracion del home.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  addHeroSlide(): void {
    this.form.hero_slides = [
      ...(this.form.hero_slides || []),
      {
        id: `hero-slide-${Date.now()}`,
        title: '',
        description: '',
        cta_href: '/products',
        image: '',
        overlay_opacity: 0.72,
        image_position: 'center',
        content_alignment: 'left',
        text_color: '#1C274C',
        button_label: 'Ver productos',
        button_color: '#1C274C'
      }
    ];
  }

  removeHeroSlide(index: number): void {
    this.form.hero_slides = (this.form.hero_slides || []).filter((_, currentIndex) => currentIndex !== index);
  }

  addHeroPromo(): void {
    this.form.hero_promos = [
      ...(this.form.hero_promos || []),
      {
        id: `hero-promo-${Date.now()}`,
        title: '',
        offer_label: 'Oferta por tiempo limitado',
        href: '/products',
        price_label: '',
        compare_price_label: '',
        image: '',
        background_color: '',
        background_image_url: ''
      }
    ];
  }

  removeHeroPromo(index: number): void {
    this.form.hero_promos = (this.form.hero_promos || []).filter((_, currentIndex) => currentIndex !== index);
  }

  addCategoryCard(): void {
    this.form.category_cards = [
      ...(this.form.category_cards || []),
      {
        id: `category-card-${Date.now()}`,
        title: '',
        href: '/products',
        image: '',
        background_color: '#F2F3F8',
        overlay_opacity: 0.18,
        image_position: 'center'
      }
    ];
  }

  removeCategoryCard(index: number): void {
    this.form.category_cards = (this.form.category_cards || []).filter((_, currentIndex) => currentIndex !== index);
  }

  addPromoBanner(): void {
    this.form.promo_banners = [
      ...(this.form.promo_banners || []),
      { id: `home-promo-${Date.now()}`, title: '', subtitle: '', description: '', cta_label: '', cta_href: '/products', image_url: '', background_color: '', accent_color: '' }
    ];
  }

  removePromoBanner(index: number): void {
    this.form.promo_banners = (this.form.promo_banners || []).filter((_, currentIndex) => currentIndex !== index);
  }

  addFeature(): void {
    this.form.features = [
      ...(this.form.features || []),
      { id: `home-feature-${Date.now()}`, title: '', description: '', image: '' }
    ];
  }

  removeFeature(index: number): void {
    this.form.features = (this.form.features || []).filter((_, currentIndex) => currentIndex !== index);
  }

  addTestimonial(): void {
    this.form.testimonials = this.form.testimonials || this.createTestimonials();
    this.form.testimonials.items = [
      ...(this.form.testimonials.items || []),
      { id: `testimonial-${Date.now()}`, review: '', author_name: '', author_role: '', author_image: '' }
    ];
  }

  removeTestimonial(index: number): void {
    this.form.testimonials = this.form.testimonials || this.createTestimonials();
    this.form.testimonials.items = (this.form.testimonials.items || []).filter((_, currentIndex) => currentIndex !== index);
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
          home: this.normalizePayload()
        }
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.editing = false;
          this.swal.success('Home guardado');
          this.loadStorefronts();
        },
        error: (err) => {
          this.saving = false;
          this.swal.error('Error', err?.error?.detail || 'No se pudo guardar el home.');
        }
      });
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    const themeSettings = (this.storefront?.theme_settings || {}) as Record<string, unknown>;
    this.form = this.normalizeForm(themeSettings['home']);
  }

  private createForm(): StorefrontHomeSettings {
    return {
      hero_slides: [],
      hero_promos: [],
      category_section: this.createSectionCopy('Explora', 'Compra por categoría'),
      category_cards: [],
      new_arrivals_section: this.createSectionCopy('Recién llegados', 'Novedades', 'Ver todos', '/products'),
      best_sellers_section: this.createSectionCopy('Lo más elegido', 'Productos destacados', 'Ver todos', '/products'),
      features: this.createDefaultFeatures(),
      promo_banners: [],
      countdown: {
        enabled: false,
        eyebrow: 'Oferta especial',
        title: 'No te pierdas esta oportunidad',
        description: 'Descubre productos seleccionados para ti.',
        cta_label: 'Ver oferta',
        cta_href: '/products',
        deadline: '2026-12-31T23:59:59',
        background_color: '#D0E9F3',
        background_image_url: '',
        product_image_url: ''
      },
      newsletter: {
        enabled: false,
        title: 'Recibe novedades y ofertas',
        description: 'Regístrate para recibir lanzamientos, descuentos y contenido de la tienda.',
        placeholder: 'Tu correo electrónico',
        button_label: 'Registrarme',
        background_image_url: ''
      },
      testimonials: this.createTestimonials()
    };
  }

  private createSectionCopy(
    eyebrow = '',
    title = '',
    ctaLabel = '',
    ctaHref = ''
  ): StorefrontHomeSectionCopy {
    return {
      eyebrow,
      title,
      cta_label: ctaLabel,
      cta_href: ctaHref
    };
  }

  private normalizeForm(input: unknown): StorefrontHomeSettings {
    const home = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};

    return {
      hero_slides: Array.isArray(home['hero_slides'])
        ? home['hero_slides']
            .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
            .map((item, index) => this.normalizeHeroSlide(item, index))
        : [],
      hero_promos: Array.isArray(home['hero_promos'])
        ? home['hero_promos']
            .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
            .map((item, index) => this.normalizeHeroPromo(item, index))
        : [],
      category_section: this.normalizeSectionCopy(home['category_section'], 'Explora', 'Compra por categoría'),
      category_cards: Array.isArray(home['category_cards'])
        ? home['category_cards']
            .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
            .map((item, index) => this.normalizeCategoryCard(item, index))
        : [],
      new_arrivals_section: this.normalizeSectionCopy(home['new_arrivals_section'], 'Recién llegados', 'Novedades', 'Ver todos', '/products'),
      best_sellers_section: this.normalizeSectionCopy(home['best_sellers_section'], 'Lo más elegido', 'Productos destacados', 'Ver todos', '/products'),
      features: Array.isArray(home['features'])
        ? home['features']
            .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
            .map((item, index) => this.normalizeFeature(item, index))
        : this.createDefaultFeatures(),
      promo_banners: Array.isArray(home['promo_banners'])
        ? home['promo_banners']
            .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
            .map((item, index) => this.normalizePromoBanner(item, index))
        : [],
      countdown: this.normalizeCountdown(home['countdown']),
      newsletter: this.normalizeNewsletter(home['newsletter']),
      testimonials: this.normalizeTestimonials(home['testimonials'])
    };
  }

  private normalizeHeroSlide(input: Record<string, unknown>, index: number): StorefrontHomeHeroSlide {
    return {
      id: String(input['id'] || `hero-slide-${index + 1}`),
      title: String(input['title'] || ''),
      description: String(input['description'] || ''),
      cta_href: String(input['cta_href'] || '/products'),
      image: String(input['image'] || ''),
      overlay_opacity: Number(input['overlay_opacity'] ?? 0.72),
      image_position: String(input['image_position'] || 'center'),
      content_alignment: String(input['content_alignment'] || 'left'),
      text_color: String(input['text_color'] || '#1C274C'),
      button_label: String(input['button_label'] || 'Ver productos'),
      button_color: String(input['button_color'] || '#1C274C')
    };
  }

  private normalizeHeroPromo(input: Record<string, unknown>, index: number): StorefrontHomeHeroPromo {
    return {
      id: String(input['id'] || `hero-promo-${index + 1}`),
      title: String(input['title'] || ''),
      offer_label: String(input['offer_label'] || 'Oferta por tiempo limitado'),
      href: String(input['href'] || '/products'),
      price_label: String(input['price_label'] || ''),
      compare_price_label: String(input['compare_price_label'] || ''),
      image: String(input['image'] || ''),
      background_color: String(input['background_color'] || ''),
      background_image_url: String(input['background_image_url'] || '')
    };
  }

  private normalizePromoBanner(input: Record<string, unknown>, index: number): StorefrontPromoBanner {
    return {
      id: String(input['id'] || `home-promo-${index + 1}`),
      title: String(input['title'] || ''),
      subtitle: String(input['subtitle'] || ''),
      description: String(input['description'] || ''),
      cta_label: String(input['cta_label'] || ''),
      cta_href: String(input['cta_href'] || '/products'),
      image_url: String(input['image_url'] || ''),
      background_color: String(input['background_color'] || ''),
      accent_color: String(input['accent_color'] || '')
    };
  }

  private normalizeCategoryCard(input: Record<string, unknown>, index: number): StorefrontHomeCategoryCard {
    return {
      id: String(input['id'] || `category-card-${index + 1}`),
      title: String(input['title'] || ''),
      href: String(input['href'] || '/products'),
      image: String(input['image'] || ''),
      background_color: String(input['background_color'] || '#F2F3F8'),
      overlay_opacity: Number(input['overlay_opacity'] ?? 0.18),
      image_position: String(input['image_position'] || 'center')
    };
  }

  private normalizeFeature(input: Record<string, unknown>, index: number): StorefrontHomeFeatureItem {
    return {
      id: String(input['id'] || `home-feature-${index + 1}`),
      title: String(input['title'] || ''),
      description: String(input['description'] || ''),
      image: String(input['image'] || '')
    };
  }

  private normalizeSectionCopy(
    input: unknown,
    eyebrow = '',
    title = '',
    ctaLabel = '',
    ctaHref = ''
  ): StorefrontHomeSectionCopy {
    const value = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      eyebrow: String(value['eyebrow'] || eyebrow),
      title: String(value['title'] || title),
      cta_label: String(value['cta_label'] || ctaLabel),
      cta_href: String(value['cta_href'] || ctaHref)
    };
  }

  private normalizeCountdown(input: unknown): StorefrontHomeCountdownSettings {
    const value = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      enabled: value['enabled'] !== false,
      eyebrow: String(value['eyebrow'] || 'Oferta especial'),
      title: String(value['title'] || 'No te pierdas esta oportunidad'),
      description: String(value['description'] || 'Descubre productos seleccionados para ti.'),
      cta_label: String(value['cta_label'] || 'Ver oferta'),
      cta_href: String(value['cta_href'] || '/products'),
      deadline: String(value['deadline'] || '2026-12-31T23:59:59'),
      background_color: String(value['background_color'] || '#D0E9F3'),
      background_image_url: String(value['background_image_url'] || ''),
      product_image_url: String(value['product_image_url'] || '')
    };
  }

  private normalizeNewsletter(input: unknown): StorefrontHomeNewsletterSettings {
    const value = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    return {
      enabled: value['enabled'] !== false,
      title: String(value['title'] || 'Recibe novedades y ofertas'),
      description: String(value['description'] || 'Regístrate para recibir lanzamientos, descuentos y contenido de la tienda.'),
      placeholder: String(value['placeholder'] || 'Tu correo electrónico'),
      button_label: String(value['button_label'] || 'Registrarme'),
      background_image_url: String(value['background_image_url'] || '')
    };
  }

  private normalizeTestimonials(input: unknown): StorefrontHomeTestimonialsSettings {
    const value = input && typeof input === 'object' ? (input as Record<string, unknown>) : {};
    const items = Array.isArray(value['items'])
      ? value['items']
          .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
          .map((item, index) => ({
            id: String(item['id'] || `testimonial-${index + 1}`),
            review: String(item['review'] || ''),
            author_name: String(item['author_name'] || ''),
            author_role: String(item['author_role'] || ''),
            author_image: String(item['author_image'] || '')
          }))
      : this.createDefaultTestimonials();

    return {
      enabled: value['enabled'] !== false,
      eyebrow: String(value['eyebrow'] || 'Testimonios'),
      title: String(value['title'] || 'Lo que dicen nuestros clientes'),
      items
    };
  }

  private normalizePayload(): StorefrontHomeSettings {
    return {
      hero_slides: (this.form.hero_slides || []).filter((item) => this.nonEmpty(item.title)),
      hero_promos: (this.form.hero_promos || []).filter((item) => this.nonEmpty(item.title)),
      category_section: this.form.category_section,
      category_cards: (this.form.category_cards || []).filter((item) => this.nonEmpty(item.title)),
      new_arrivals_section: this.form.new_arrivals_section,
      best_sellers_section: this.form.best_sellers_section,
      features: (this.form.features || []).filter((item) => this.nonEmpty(item.title)),
      promo_banners: (this.form.promo_banners || []).filter((item) => this.nonEmpty(item.title)),
      countdown: this.form.countdown,
      newsletter: this.form.newsletter,
      testimonials: {
        ...(this.form.testimonials || this.createTestimonials()),
        items: (this.form.testimonials?.items || []).filter((item) => this.nonEmpty(item.review) && this.nonEmpty(item.author_name))
      }
    };
  }

  private nonEmpty(value: unknown): boolean {
    return String(value || '').trim().length > 0;
  }

  private createDefaultFeatures(): StorefrontHomeFeatureItem[] {
    return [
      {
        id: 'feature-1',
        title: 'Envíos confiables',
        description: 'Consulta condiciones de entrega',
        image: '/images/icons/icon-01.svg'
      },
      {
        id: 'feature-2',
        title: 'Cambios y devoluciones',
        description: 'Compra con tranquilidad',
        image: '/images/icons/icon-02.svg'
      },
      {
        id: 'feature-3',
        title: 'Pagos seguros',
        description: 'Tus datos siempre protegidos',
        image: '/images/icons/icon-03.svg'
      },
      {
        id: 'feature-4',
        title: 'Atención al cliente',
        description: 'Estamos para ayudarte',
        image: '/images/icons/icon-04.svg'
      }
    ];
  }

  private createTestimonials(): StorefrontHomeTestimonialsSettings {
    return {
      enabled: false,
      eyebrow: 'Testimonios',
      title: 'Lo que dicen nuestros clientes',
      items: this.createDefaultTestimonials()
    };
  }

  private createDefaultTestimonials() {
    return [
      {
        id: 'testimonial-1',
        review: 'Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula',
        author_name: 'Davis Dorwart',
        author_role: 'Serial Entrepreneur',
        author_image: '/images/users/user-01.jpg'
      },
      {
        id: 'testimonial-2',
        review: 'Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula',
        author_name: 'Wilson Dias',
        author_role: 'Backend Developer',
        author_image: '/images/users/user-02.jpg'
      },
      {
        id: 'testimonial-3',
        review: 'Lorem ipsum dolor sit amet, adipiscing elit. Donec malesuada justo vitaeaugue suscipit beautiful vehicula',
        author_name: 'Miracle Exterm',
        author_role: 'Serial Entrepreneur',
        author_image: '/images/users/user-03.jpg'
      }
    ];
  }
}
