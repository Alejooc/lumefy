import { Component, ElementRef, HostListener, Input, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

export type EcommerceEditorPageId = 'home' | 'product' | 'collection' | 'search' | 'cart' | 'pages';

interface EcommerceEditorPageOption {
  id: EcommerceEditorPageId;
  label: string;
  description: string;
  icon: string;
  route: string;
}

const EDITOR_PAGES: EcommerceEditorPageOption[] = [
  { id: 'home', label: 'Página de inicio', description: 'Secciones principales', icon: 'home', route: '/commerce/design' },
  { id: 'product', label: 'Producto', description: 'Ficha, galería y compra', icon: 'shopping-bag', route: '/commerce/design/product' },
  { id: 'collection', label: 'Colecciones', description: 'Catálogo, filtros y orden', icon: 'category', route: '/commerce/design/collection' },
  { id: 'search', label: 'Resultados de búsqueda', description: 'Resultados y estado vacío', icon: 'search', route: '/commerce/design/search' },
  { id: 'cart', label: 'Carrito', description: 'Productos y resumen', icon: 'shopping-cart', route: '/commerce/design/cart' },
  { id: 'pages', label: 'Páginas informativas', description: 'Contacto, contenido y políticas', icon: 'file-text', route: '/commerce/design/pages' },
];

@Component({
  selector: 'app-ecommerce-editor-page-picker',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './ecommerce-editor-page-picker.component.html',
  styleUrls: ['./ecommerce-editor-page-picker.component.scss'],
})
export class EcommerceEditorPagePickerComponent {
  @Input() activePage: EcommerceEditorPageId = 'home';
  @Input() hasUnsavedChanges = false;

  readonly pages = EDITOR_PAGES;
  menuOpen = false;

  private host = inject(ElementRef<HTMLElement>);

  get activeOption(): EcommerceEditorPageOption {
    return this.pages.find((page) => page.id === this.activePage) || this.pages[0];
  }

  toggleMenu(): void {
    this.menuOpen = !this.menuOpen;
  }

  closeMenu(): void {
    this.menuOpen = false;
  }

  onNavigate(event: MouseEvent): void {
    if (this.hasUnsavedChanges && !window.confirm('Tienes cambios sin guardar. ¿Quieres cambiar de página y descartarlos?')) {
      event.preventDefault();
      return;
    }
    this.closeMenu();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) this.closeMenu();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeMenu();
  }
}
