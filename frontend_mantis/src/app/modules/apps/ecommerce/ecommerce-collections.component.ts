import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import {
  PublishedProduct,
  StoreCollection,
  StoreCollectionProduct,
  Storefront,
  StorefrontAdminService
} from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-ecommerce-collections',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-collections.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-collections.component.scss']
})
export class EcommerceCollectionsComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  collections: StoreCollection[] = [];
  publishedProducts: PublishedProduct[] = [];
  collectionProducts: StoreCollectionProduct[] = [];
  viewMode: 'list' | 'detail' = 'list';
  showConfigPanel = false;
  showAddProductsModal = false;
  selectedCollectionId = '';
  form: Partial<StoreCollection> = this.createForm();
  assignment = { publishedProductId: '', sortOrder: 0 };
  availableSearch = '';
  linkedSearch = '';
  availableSlugFilter = '';
  linkedSlugFilter = '';
  availableFeaturedFilter: 'all' | 'featured' | 'regular' = 'all';
  linkedFeaturedFilter: 'all' | 'featured' | 'regular' = 'all';
  availableMinPrice: number | null = null;
  availableMaxPrice: number | null = null;
  linkedMinPrice: number | null = null;
  linkedMaxPrice: number | null = null;
  selectedAvailableProductIds: string[] = [];
  selectedLinkedProductIds: string[] = [];

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadData();
  }

  get selectedCollection(): StoreCollection | null {
    return this.collections.find((item) => item.id === this.selectedCollectionId) || null;
  }

  get linkedProducts(): PublishedProduct[] {
    const linkedIds = new Set(this.collectionProducts.map((item) => item.published_product_id));
    return this.publishedProducts.filter((item) => linkedIds.has(item.id));
  }

  get availableProducts(): PublishedProduct[] {
    const linkedIds = new Set(this.collectionProducts.map((item) => item.published_product_id));
    return this.publishedProducts.filter((item) => !linkedIds.has(item.id));
  }

  get filteredAvailableProducts(): PublishedProduct[] {
    return this.availableProducts.filter((item) =>
      this.matchesFilters(
        item,
        this.availableSearch,
        this.availableSlugFilter,
        this.availableFeaturedFilter,
        this.availableMinPrice,
        this.availableMaxPrice
      )
    );
  }

  get filteredLinkedProducts(): PublishedProduct[] {
    return this.linkedProducts.filter((item) =>
      this.matchesFilters(
        item,
        this.linkedSearch,
        this.linkedSlugFilter,
        this.linkedFeaturedFilter,
        this.linkedMinPrice,
        this.linkedMaxPrice
      )
    );
  }

  loadData(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.loadCollections();
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar las colecciones.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.resetSelection();
    this.loadCollections();
  }

  loadCollections(): void {
    if (!this.selectedStorefrontId) {
      this.collections = [];
      this.publishedProducts = [];
      this.collectionProducts = [];
      this.loading = false;
      return;
    }
    this.loading = true;
    forkJoin({
      collections: this.storefrontService.getCollections(this.selectedStorefrontId),
      products: this.storefrontService.getPublishedProducts(this.selectedStorefrontId)
    }).subscribe({
      next: ({ collections, products }) => {
        this.collections = collections;
        this.publishedProducts = products;
        this.resetBulkSelection();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la data de colecciones.');
      }
    });
  }

  openCollection(collectionId: string): void {
    this.selectedCollectionId = collectionId;
    const selected = this.collections.find((item) => item.id === collectionId);
    this.form = selected ? { ...selected } : this.createForm();
    this.assignment = { publishedProductId: '', sortOrder: 0 };
    this.resetFilters();
    this.resetBulkSelection();
    this.viewMode = 'detail';
    this.showConfigPanel = false;
    this.showAddProductsModal = false;
    if (!collectionId) {
      this.collectionProducts = [];
      return;
    }
    this.loadCollectionProducts(collectionId);
  }

  loadCollectionProducts(collectionId: string): void {
    this.storefrontService.getCollectionProducts(collectionId).subscribe({
      next: (items) => {
        this.collectionProducts = items;
        this.selectedLinkedProductIds = [];
      },
      error: (err) => {
        this.collectionProducts = [];
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar los productos de la coleccion.');
      }
    });
  }

  startNewCollection(): void {
    this.resetSelection();
    this.viewMode = 'detail';
    this.showConfigPanel = true;
  }

  save(): void {
    if (!this.selectedStorefrontId) return;
    this.saving = true;
    const payload = {
      ...this.form,
      storefront_id: this.selectedStorefrontId,
      name: this.form.name?.trim(),
      slug: this.form.slug?.trim()
    };
    const request = this.selectedCollectionId
      ? this.storefrontService.updateCollection(this.selectedCollectionId, payload)
      : this.storefrontService.createCollection(payload);
    request.subscribe({
      next: (collection) => {
        this.saving = false;
        this.swal.success('Coleccion guardada');
        this.selectedCollectionId = collection.id;
        this.viewMode = 'detail';
        this.showConfigPanel = false;
        this.showAddProductsModal = false;
        this.loadCollections();
        this.loadCollectionProducts(collection.id);
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar la coleccion.');
      }
    });
  }

  assign(): void {
    if (!this.selectedCollectionId || !this.assignment.publishedProductId) {
      this.swal.warning('Faltan datos', 'Selecciona coleccion y producto publicado.');
      return;
    }
    this.saving = true;
    this.storefrontService.addProductToCollection(this.selectedCollectionId, {
      published_product_id: this.assignment.publishedProductId,
      sort_order: this.assignment.sortOrder
    }).subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Producto agregado a la coleccion');
        this.assignment = { publishedProductId: '', sortOrder: 0 };
        this.loadCollectionProducts(this.selectedCollectionId);
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo agregar el producto.');
      }
    });
  }

  openAddProductsModal(): void {
    if (!this.selectedCollectionId) return;
    this.availableSearch = '';
    this.availableSlugFilter = '';
    this.availableFeaturedFilter = 'all';
    this.availableMinPrice = null;
    this.availableMaxPrice = null;
    this.selectedAvailableProductIds = [];
    this.assignment.sortOrder = this.nextSortOrder();
    this.showAddProductsModal = true;
  }

  closeAddProductsModal(): void {
    this.showAddProductsModal = false;
    this.availableSearch = '';
    this.availableSlugFilter = '';
    this.availableFeaturedFilter = 'all';
    this.availableMinPrice = null;
    this.availableMaxPrice = null;
    this.selectedAvailableProductIds = [];
  }

  toggleAvailableSelection(productId: string, checked: boolean): void {
    this.selectedAvailableProductIds = checked
      ? Array.from(new Set([...this.selectedAvailableProductIds, productId]))
      : this.selectedAvailableProductIds.filter((id) => id !== productId);
  }

  toggleLinkedSelection(productId: string, checked: boolean): void {
    this.selectedLinkedProductIds = checked
      ? Array.from(new Set([...this.selectedLinkedProductIds, productId]))
      : this.selectedLinkedProductIds.filter((id) => id !== productId);
  }

  toggleSelectAllAvailable(checked: boolean): void {
    const filteredIds = this.filteredAvailableProducts.map((item) => item.id);
    if (checked) {
      this.selectedAvailableProductIds = Array.from(new Set([...this.selectedAvailableProductIds, ...filteredIds]));
      return;
    }
    this.selectedAvailableProductIds = this.selectedAvailableProductIds.filter((id) => !filteredIds.includes(id));
  }

  toggleSelectAllLinked(checked: boolean): void {
    const filteredIds = this.filteredLinkedProducts.map((item) => item.id);
    if (checked) {
      this.selectedLinkedProductIds = Array.from(new Set([...this.selectedLinkedProductIds, ...filteredIds]));
      return;
    }
    this.selectedLinkedProductIds = this.selectedLinkedProductIds.filter((id) => !filteredIds.includes(id));
  }

  isAvailableSelected(productId: string): boolean {
    return this.selectedAvailableProductIds.includes(productId);
  }

  isLinkedSelected(productId: string): boolean {
    return this.selectedLinkedProductIds.includes(productId);
  }

  areAllFilteredAvailableSelected(): boolean {
    return this.filteredAvailableProducts.length > 0 && this.filteredAvailableProducts.every((item) => this.isAvailableSelected(item.id));
  }

  areAllFilteredLinkedSelected(): boolean {
    return this.filteredLinkedProducts.length > 0 && this.filteredLinkedProducts.every((item) => this.isLinkedSelected(item.id));
  }

  addSelectedProducts(): void {
    if (!this.selectedCollectionId || this.selectedAvailableProductIds.length === 0) {
      this.swal.warning('Faltan datos', 'Selecciona al menos un producto para agregar.');
      return;
    }

    const startingSortOrder = Number(this.assignment.sortOrder || this.nextSortOrder());
    const requests = this.selectedAvailableProductIds.map((productId, index) =>
      this.storefrontService.addProductToCollection(this.selectedCollectionId, {
        published_product_id: productId,
        sort_order: startingSortOrder + index
      })
    );

    this.saving = true;
    forkJoin(requests).subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Productos agregados a la coleccion');
        this.closeAddProductsModal();
        this.loadCollectionProducts(this.selectedCollectionId!);
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudieron agregar los productos.');
      }
    });
  }

  removeLinkedProduct(publishedProductId: string): void {
    if (!this.selectedCollectionId) return;
    this.storefrontService.removeProductFromCollection(this.selectedCollectionId, publishedProductId).subscribe({
      next: () => {
        this.swal.success('Producto eliminado de la coleccion');
        this.loadCollectionProducts(this.selectedCollectionId);
      },
      error: (err) => {
        this.swal.error('Error', err?.error?.detail || 'No se pudo eliminar el producto de la coleccion.');
      }
    });
  }

  removeSelectedLinkedProducts(): void {
    if (!this.selectedCollectionId || this.selectedLinkedProductIds.length === 0) {
      this.swal.warning('Sin seleccion', 'Selecciona productos de la coleccion para eliminarlos.');
      return;
    }

    const requests = this.selectedLinkedProductIds.map((productId) =>
      this.storefrontService.removeProductFromCollection(this.selectedCollectionId!, productId)
    );

    this.saving = true;
    forkJoin(requests).subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Productos eliminados de la coleccion');
        this.loadCollectionProducts(this.selectedCollectionId!);
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudieron eliminar los productos seleccionados.');
      }
    });
  }

  linkedSortOrder(publishedProductId: string): number {
    return this.collectionProducts.find((item) => item.published_product_id === publishedProductId)?.sort_order || 0;
  }

  productLabel(item: PublishedProduct): string {
    return item.product_name || item.slug;
  }

  priceLabel(item: PublishedProduct): string {
    const base = item.base_price ?? null;
    if (base === null) {
      return 'Sin precio';
    }
    return `Precio ERP ${base}`;
  }

  backToList(): void {
    this.viewMode = 'list';
    this.showConfigPanel = false;
  }

  toggleConfigPanel(): void {
    this.showConfigPanel = !this.showConfigPanel;
  }

  private resetSelection(): void {
    this.selectedCollectionId = '';
    this.form = this.createForm();
    this.collectionProducts = [];
    this.assignment = { publishedProductId: '', sortOrder: 0 };
    this.resetFilters();
    this.resetBulkSelection();
    this.showAddProductsModal = false;
  }

  private matchesSearch(item: PublishedProduct, query: string): boolean {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return true;
    }

    return [item.product_name, item.product_description, item.slug]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalized));
  }

  private matchesFilters(
    item: PublishedProduct,
    query: string,
    slugFilter: string,
    featuredFilter: 'all' | 'featured' | 'regular',
    minPrice: number | null,
    maxPrice: number | null
  ): boolean {
    const matchesText = this.matchesSearch(item, query);
    const matchesSlug = !slugFilter.trim() || item.slug.toLowerCase().includes(slugFilter.trim().toLowerCase());
    const matchesFeatured =
      featuredFilter === 'all' ||
      (featuredFilter === 'featured' && item.is_featured) ||
      (featuredFilter === 'regular' && !item.is_featured);

    const price = item.base_price;
    const matchesMinPrice = minPrice === null || price === null || price === undefined || price >= minPrice;
    const matchesMaxPrice = maxPrice === null || price === null || price === undefined || price <= maxPrice;

    return matchesText && matchesSlug && matchesFeatured && matchesMinPrice && matchesMaxPrice;
  }

  private resetFilters(): void {
    this.availableSearch = '';
    this.linkedSearch = '';
    this.availableSlugFilter = '';
    this.linkedSlugFilter = '';
    this.availableFeaturedFilter = 'all';
    this.linkedFeaturedFilter = 'all';
    this.availableMinPrice = null;
    this.availableMaxPrice = null;
    this.linkedMinPrice = null;
    this.linkedMaxPrice = null;
  }

  private resetBulkSelection(): void {
    this.selectedAvailableProductIds = [];
    this.selectedLinkedProductIds = [];
  }

  private nextSortOrder(): number {
    if (this.collectionProducts.length === 0) {
      return 1;
    }
    return Math.max(...this.collectionProducts.map((item) => item.sort_order || 0)) + 1;
  }

  private createForm(): Partial<StoreCollection> {
    return {
      name: '',
      slug: '',
      description: '',
      image_url: '',
      is_visible: true,
      is_featured: false,
      sort_order: 0
    };
  }
}
