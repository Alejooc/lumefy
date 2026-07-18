import { Component, OnInit, inject, ChangeDetectorRef, ViewEncapsulation, ElementRef, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { LandingService, LandingConfig, Plan } from 'src/app/core/services/landing.service';

@Component({
  selector: 'app-landing-page',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './landing-page.html',
  styleUrl: './landing-page.scss',
  encapsulation: ViewEncapsulation.None // Critical for global overrides/dark theme
})
export class LandingPage implements OnInit, OnDestroy {
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
            { title: 'Catálogo e inventario', description: 'Centraliza productos, stock, compras y movimientos por sucursal.', icon: 'box-seam' },
            { title: 'Ventas y punto de venta', description: 'Gestiona cotizaciones, pedidos, caja y devoluciones desde un mismo lugar.', icon: 'cart-check' },
            { title: 'Tienda online', description: 'Publica tu catálogo y configura branding, checkout, pagos y dominios.', icon: 'shop' },
            { title: 'Logística', description: 'Prepara picking, empaques y fulfillment a partir de tus pedidos.', icon: 'truck' },
            { title: 'Clientes y equipo', description: 'Organiza clientes, usuarios, roles y permisos por empresa.', icon: 'people' },
            { title: 'Reportes operativos', description: 'Consulta ventas, pedidos e indicadores para tomar decisiones.', icon: 'graph-up-arrow' }
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
            title: 'Opera tu negocio y vende online desde un solo lugar',
            subtitle: 'Lumefy conecta catálogo, inventario, ventas, logística y tienda online para que tu operación avance sin duplicar trabajo.',
            cta_text: 'Crear mi empresa',
            cta_link: "/register",
            image_url: "assets/images/auth/auth-bg.png"
          },
          features: [
            { title: 'Catálogo e inventario', description: 'Centraliza productos, stock, compras y movimientos por sucursal.', icon: 'box-seam' },
            { title: 'Ventas y punto de venta', description: 'Gestiona cotizaciones, pedidos, caja y devoluciones desde un mismo lugar.', icon: 'cart-check' },
            { title: 'Tienda online', description: 'Publica tu catálogo y configura branding, checkout, pagos y dominios.', icon: 'shop' },
            { title: 'Logística', description: 'Prepara picking, empaques y fulfillment a partir de tus pedidos.', icon: 'truck' },
            { title: 'Clientes y equipo', description: 'Organiza clientes, usuarios, roles y permisos por empresa.', icon: 'people' },
            { title: 'Reportes operativos', description: 'Consulta ventas, pedidos e indicadores para tomar decisiones.', icon: 'graph-up-arrow' }
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

  faqs = [
    {
      question: '¿Cómo empiezo a operar en Lumefy?',
      answer: 'Crea tu empresa y sucursal, agrega el catálogo y registra cotizaciones o pedidos. Desde el dashboard encontrarás el orden recomendado.'
    },
    {
      question: '¿Puedo manejar varias sucursales?',
      answer: 'Sí. Puedes registrar sucursales y consultar la operación por sucursal desde los módulos de inventario, ventas y dashboard.'
    },
    {
      question: '¿La tienda online es obligatoria?',
      answer: 'No. Puedes operar solamente con ventas internas o activar la tienda cuando tu catálogo y operación estén listos.'
    },
    {
      question: '¿Cómo publico productos en la tienda?',
      answer: 'Primero crea la tienda online, luego configura los productos, el branding y los pagos desde el módulo de Ecommerce.'
    },
    {
      question: '¿Dónde configuro usuarios y permisos?',
      answer: 'En Gestión puedes crear usuarios, asignar roles y definir qué puede hacer cada integrante de tu equipo.'
    }
  ];

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

  // FAQ Accordion State
  openFaqIndex: number | null = null;

  toggleFaq(index: number) {
    if (this.openFaqIndex === index) {
      this.openFaqIndex = null; // Close if already open
    } else {
      this.openFaqIndex = index; // Open clicked
    }
  }

  getPlanButtonText(plan: Plan): string {
    if (plan.button_text) return plan.button_text;

    // Fallback defaults
    if (plan.code === 'FREE') return 'Crear Cuenta Gratis';
    if (plan.code === 'PRO') return 'Comenzar Prueba Gratis';
    if (plan.code === 'ENTERPRISE') return 'Contactar Ventas';
    return 'Seleccionar Plan';
  }

  getPlanFeatures(plan: Plan): string[] {
    if (!plan.features) return [];
    if (Array.isArray(plan.features)) {
      return plan.features.filter((feature): feature is string => typeof feature === 'string');
    }
    if (typeof plan.features === 'object') {
      const featureMap = plan.features as Record<string, unknown>;
      return Object.keys(featureMap).filter((key) => featureMap[key] === true || featureMap[key] === 'true');
    }
    return [];
  }
}
