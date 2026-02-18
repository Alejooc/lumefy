import { Component, OnInit, inject, ChangeDetectorRef, ViewEncapsulation, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { LandingService, LandingConfig } from 'src/app/core/services/landing.service';

@Component({
  selector: 'app-landing-page',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './landing-page.html',
  styleUrl: './landing-page.scss',
  encapsulation: ViewEncapsulation.None // Critical for global overrides/dark theme
})
export class LandingPage implements OnInit, AfterViewInit, OnDestroy {
  private landingService = inject(LandingService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild('scrollSentinel') scrollSentinel!: ElementRef;
  private observer: IntersectionObserver | undefined;

  config: LandingConfig;
  isLoading = true;
  isMenuOpen = false;
  isScrolled = false;

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  ngOnInit() {
    this.landingService.getLandingConfig().subscribe({
      next: (data) => {
        this.config = data;

        // Ensure features have data (Fallback if API returns empty list)
        if (!this.config.features || this.config.features.length === 0) {
          this.config.features = [
            { title: "Inventario Inteligente", description: "Control de stock en tiempo real con alertas predictivas.", icon: "box-seam" },
            { title: "Punto de Venta POS", description: "Vende en segundos. Facturación electrónica integrada.", icon: "cart-check" },
            { title: "Analítica Avanzada", description: "Reportes financieros para decisiones basadas en datos.", icon: "graph-up-arrow" },
            { title: "CRM Integrado", description: "Gestiona fidelización y aumenta tus ventas.", icon: "people" },
            { title: "100% en la Nube", description: "Accede desde cualquier lugar con seguridad total.", icon: "cloud-check" },
            { title: "App Móvil", description: "Lleva tu negocio en el bolsillo.", icon: "phone" }
          ];
        }

        // Ensure clients have data for visual demo if empty
        if (!this.config.clients || this.config.clients.length === 0) {
          // HTML handles fallback
        }

        this.isLoading = false;

        // Trigger change detection and setup observer after view renders
        this.cdr.detectChanges();
        setTimeout(() => this.setupObserver(), 100);
      },
      error: (err) => {
        console.error('LandingPage: API error', err);
        // Fallback default config if API fails completely
        this.config = {
          enabled: true,
          hero: {
            title: "Revoluciona la Gestión de tu Empresa",
            subtitle: "La plataforma all-in-one.",
            cta_text: "Prueba Gratis",
            cta_link: "/register",
            image_url: "assets/images/auth/auth-bg.png"
          },
          features: [
            { title: "Inventario Inteligente", description: "Control de stock en tiempo real.", icon: "box-seam" },
            { title: "Punto de Venta POS", description: "Facturación electrónica integrada.", icon: "cart-check" },
            { title: "Analítica Avanzada", description: "Reportes financieros detallados.", icon: "graph-up-arrow" },
            { title: "CRM Integrado", description: "Gestiona fidelización de clientes.", icon: "people" },
            { title: "100% en la Nube", description: "Acceso seguro desde cualquier lugar.", icon: "cloud-check" },
            { title: "App Móvil", description: "Tu negocio en el bolsillo.", icon: "phone" }
          ],
          clients: [],
          social: {},
          contact: {
            email: "hola@lumefy.io",
            phone: "+57 (601) 555-0123",
            address: "Bogotá, Colombia"
          },
          pricing_visible: true
        };
        this.isLoading = false;
        this.cdr.detectChanges();
        setTimeout(() => this.setupObserver(), 100);
      }
    });
  }

  ngAfterViewInit() {
    // We defer observer setup to ngOnInit data load to ensure sentinel exists
  }

  setupObserver() {
    if (!this.scrollSentinel) return;

    // Disconnect existing if any
    if (this.observer) this.observer.disconnect();

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        // If sentinel (at top) is NOT intersecting, we have scrolled past it
        const isNowScrolled = !entry.isIntersecting;

        if (this.isScrolled !== isNowScrolled) {
          this.isScrolled = isNowScrolled;
          this.cdr.detectChanges();
        }
      });
    }, { root: null, threshold: 0 });

    this.observer.observe(this.scrollSentinel.nativeElement);
  }

  ngOnDestroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  scrollTo(elementId: string) {
    this.closeMenu();
    const element = document.getElementById(elementId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  }

  navigateToLogin() {
    this.router.navigate(['/login']);
  }

  getPlanFeatures(plan: any): string[] {
    if (!plan.features) return [];
    if (Array.isArray(plan.features)) {
      return plan.features;
    }
    if (typeof plan.features === 'object') {
      // If it's a dict like { "Feature": true, "Other": false }, return keys where value is true
      return Object.keys(plan.features).filter(key => plan.features[key] === true || plan.features[key] === 'true');
    }
    return [];
  }
}
