import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';
import { ExportService } from '../../../core/services/export.service';
import { Product } from '../../../core/services/product.service';

interface BulkDeleteBlockedProduct {
    id: string;
    name: string;
    reasons: string[];
}

interface BulkDeleteResponse {
    requested: number;
    deleted: number;
    deleted_ids: string[];
    archived: number;
    archived_ids: string[];
    blocked: BulkDeleteBlockedProduct[];
    not_found: string[];
}

interface BulkImageUrlResponse {
    requested: number;
    products_updated: number;
    images_updated: number;
    skipped_valid: number;
    not_found: string[];
}

interface BulkPublishResponse {
    requested: number;
    published: number;
    reactivated: number;
    already_published: number;
    not_found: string[];
}

interface ProductPageResponse {
    items: Product[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

@Component({
    selector: 'app-product-list',
    standalone: false,
    templateUrl: './product-list.component.html',
    styleUrls: ['./product-list.component.scss']
})
export class ProductListComponent implements OnInit {
    private apiService = inject(ApiService);
    private swal = inject(SweetAlertService);
    private auth = inject(AuthService);
    private cdr = inject(ChangeDetectorRef);
    private exportService = inject(ExportService);

    products: Product[] = [];
    isLoading = false;
    searchQuery = '';
    selectedProductIds = new Set<string>();
    page = 1;
    // Fifty rows keeps the admin table responsive while preserving the
    // existing pagination and the optional 100-row choice for bulk review.
    pageSize = 50;
    totalProducts = 0;
    totalPages = 0;

    currencySymbol = '$';

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        this.loadProducts();
    }

    loadProducts() {
        this.isLoading = true;
        const params: Record<string, string | number> = {
            page: this.page,
            page_size: this.pageSize
        };
        if (this.searchQuery.trim()) {
            params['search'] = this.searchQuery.trim();
        }
        this.apiService.get<ProductPageResponse>('/products/paged', params).subscribe({
            next: (data) => {
                this.products = data.items;
                this.totalProducts = data.total;
                this.totalPages = data.total_pages;
                this.page = data.page;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Error loading products', err);
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }

    onSearch() {
        this.clearSelection();
        this.page = 1;
        this.loadProducts();
    }

    onPageSizeChange(value: number | string): void {
        const nextPageSize = Number(value);
        if (!Number.isFinite(nextPageSize) || nextPageSize < 1 || nextPageSize > 100) {
            return;
        }
        this.pageSize = nextPageSize;
        this.page = 1;
        this.clearSelection();
        this.loadProducts();
    }

    goToPage(page: number): void {
        if (page < 1 || page > this.totalPages || page === this.page || this.isLoading) {
            return;
        }
        this.page = page;
        this.loadProducts();
    }

    get pageNumbers(): number[] {
        const maxVisiblePages = 7;
        if (this.totalPages <= maxVisiblePages) {
            return Array.from({ length: this.totalPages }, (_, index) => index + 1);
        }

        let start = Math.max(1, this.page - 3);
        const end = Math.min(this.totalPages, start + maxVisiblePages - 1);
        start = Math.max(1, end - maxVisiblePages + 1);
        return Array.from({ length: end - start + 1 }, (_, index) => start + index);
    }

    get firstVisibleProduct(): number {
        return this.totalProducts ? ((this.page - 1) * this.pageSize) + 1 : 0;
    }

    get lastVisibleProduct(): number {
        return Math.min(this.page * this.pageSize, this.totalProducts);
    }

    isSelected(productId: string | undefined): boolean {
        return Boolean(productId && this.selectedProductIds.has(productId));
    }

    get selectedCount(): number {
        return this.selectedProductIds.size;
    }

    allVisibleSelected(): boolean {
        return this.products.length > 0 && this.products.every((product) => this.isSelected(product.id));
    }

    someVisibleSelected(): boolean {
        return this.products.some((product) => this.isSelected(product.id)) && !this.allVisibleSelected();
    }

    toggleSelection(productId: string | undefined, checked: boolean): void {
        if (!productId) {
            return;
        }
        if (checked) {
            this.selectedProductIds.add(productId);
        } else {
            this.selectedProductIds.delete(productId);
        }
    }

    toggleAllVisible(checked: boolean): void {
        this.products.forEach((product) => {
            if (!product.id) {
                return;
            }
            if (checked) {
                this.selectedProductIds.add(product.id);
            } else {
                this.selectedProductIds.delete(product.id);
            }
        });
    }

    clearSelection(): void {
        this.selectedProductIds.clear();
    }

    getTypeLabel(type: string): string {
        switch (type) {
            case 'STORABLE': return 'Almacenable';
            case 'CONSUMABLE': return 'Consumible';
            case 'SERVICE': return 'Servicio';
            default: return type || 'Almacenable';
        }
    }

    getTypeBadgeClass(type: string): string {
        switch (type) {
            case 'STORABLE': return 'badge bg-primary';
            case 'CONSUMABLE': return 'badge bg-warning text-dark';
            case 'SERVICE': return 'badge bg-info';
            default: return 'badge bg-secondary';
        }
    }

    deleteProduct(id: string) {
        this.swal.confirmDelete().then((confirmed) => {
            if (confirmed) {
                this.isLoading = true;
                this.apiService.delete(`/products/${id}`).subscribe({
                    next: () => {
                        this.swal.success('Eliminado', 'Producto eliminado correctamente.');
                        this.loadProducts();
                    },
                    error: (err) => {
                        console.error('Error deleting product', err);
                        const detail = err?.error?.detail;
                        this.swal.error(
                            'No se pudo eliminar',
                            typeof detail === 'string' ? detail : 'El producto tiene relaciones que deben conservarse.'
                        );
                        this.isLoading = false;
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }

    deleteSelected(): void {
        const productIds = Array.from(this.selectedProductIds);
        if (!productIds.length) {
            return;
        }

        this.swal
            .confirm(
                '¿Eliminar productos seleccionados?',
                `Se revisarán ${productIds.length} producto(s). Los que estén relacionados con ventas, inventario u otros documentos se conservarán.`
            )
            .then((result) => {
                if (!result.isConfirmed) {
                    return;
                }

                this.isLoading = true;
                this.apiService
                    .post<BulkDeleteResponse>('/products/bulk-delete', { product_ids: productIds })
                    .subscribe({
                        next: (response) => {
                            this.clearSelection();
                            this.showBulkDeleteResult(response);
                        },
                        error: (err) => {
                            console.error('Error deleting selected products', err);
                            const detail = err?.error?.detail;
                            this.swal.error(
                                'No se pudo completar el borrado',
                                typeof detail === 'string' ? detail : 'Intenta nuevamente.'
                            );
                            this.isLoading = false;
                            this.cdr.detectChanges();
                        }
                    });
            });
    }

    deleteAllProducts(): void {
        if (!this.totalProducts || this.isLoading) {
            return;
        }

        const scope = this.searchQuery.trim()
            ? 'Se eliminará todo el catálogo, aunque un producto no coincida con la búsqueda actual.'
            : `Se procesarán los ${this.totalProducts} producto(s) de todas las páginas.`;
        this.swal
            .confirm(
                '¿Eliminar todo el catálogo?',
                `${scope} Los productos sin historial se eliminarán. Los que tengan ventas, facturas o inventario se archivarán y dejarán de aparecer en el catálogo/ecommerce, conservando intacto el historial. Esta acción no se puede deshacer desde el panel.`
            )
            .then((result) => {
                if (!result.isConfirmed) {
                    return;
                }

                this.isLoading = true;
                this.apiService.post<BulkDeleteResponse>('/products/bulk-delete-all', { force: true }).subscribe({
                    next: (response) => {
                        this.clearSelection();
                        this.page = 1;
                        this.showBulkDeleteResult(response, 'Catálogo eliminado');
                    },
                    error: (err) => {
                        console.error('Error deleting all products', err);
                        const detail = err?.error?.detail;
                        this.swal.error(
                            'No se pudo completar el borrado global',
                            typeof detail === 'string' ? detail : 'Intenta nuevamente.'
                        );
                        this.isLoading = false;
                        this.cdr.detectChanges();
                    }
                });
            });
        }

    async completeImageUrls(): Promise<void> {
        if (this.isLoading || !this.totalProducts) {
            return;
        }

        const selectedIds = Array.from(this.selectedProductIds);
        const scopeText = selectedIds.length
            ? `Se revisarán los ${selectedIds.length} productos seleccionados.`
            : `Se revisarán los ${this.totalProducts} productos del catálogo completo.`;
        const result = await this.swal.input({
            title: 'Completar URLs de imágenes',
            text: `${scopeText} Las rutas relativas se completarán conservando todos sus directorios. Las URLs absolutas se conservarán por ahora y podrás reemplazarlas si quedaron con una base incorrecta.`,
            input: 'text',
            inputLabel: 'Base de imágenes',
            inputPlaceholder: 'https://cdn.proveedor.com/',
            inputAttributes: { autocapitalize: 'off', autocorrect: 'off' },
            showCancelButton: true,
            confirmButtonText: 'Revisar URLs',
            cancelButtonText: 'Cancelar',
            inputValidator: (value) => {
                const prefix = String(value || '').trim();
                try {
                    const parsed = new URL(prefix);
                    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname) {
                        return 'Escribe una URL completa que empiece por http:// o https://.';
                    }
                } catch {
                    return 'Escribe una URL completa que empiece por http:// o https://.';
                }
                return undefined;
            }
        });
        if (!result.isConfirmed) {
            return;
        }

        const body: { prefix: string; product_ids?: string[]; replace_existing?: boolean } = {
            prefix: String(result.value).trim()
        };
        if (selectedIds.length) {
            body.product_ids = selectedIds;
        }

        this.isLoading = true;
        this.updateImageUrls(body, false);
    }

    private updateImageUrls(
        body: { prefix: string; product_ids?: string[]; replace_existing?: boolean },
        replacingExisting: boolean
    ): void {
        this.apiService.post<BulkImageUrlResponse>('/products/bulk-complete-image-urls', body).subscribe({
            next: (response) => {
                if (!replacingExisting && response.skipped_valid > 0) {
                    this.swal
                        .confirm(
                            'Hay URLs existentes',
                            `${response.skipped_valid} imagen(es) ya tienen una URL absoluta. Si esa base es incorrecta, se reemplazarán conservando la ruta completa del proveedor (por ejemplo products/12529/9_b4.jpg). ¿Continuar?`
                        )
                        .then((confirmation) => {
                            if (confirmation.isConfirmed) {
                                body.replace_existing = true;
                                this.updateImageUrls(body, true);
                                return;
                            }
                            this.clearSelection();
                            this.isLoading = false;
                            this.loadProducts();
                        });
                    return;
                }

                this.clearSelection();
                this.isLoading = false;
                const replacedText = replacingExisting ? ' Las bases anteriores fueron reemplazadas.' : '';
                this.swal.success(
                    'URLs actualizadas',
                    `${response.images_updated} imagen(es) actualizada(s). ${response.skipped_valid} URL(s) válida(s) se conservaron.${replacedText}`
                );
                this.loadProducts();
            },
            error: (err) => {
                this.isLoading = false;
                const detail = err?.error?.detail;
                this.swal.error('No se pudieron completar las URLs', typeof detail === 'string' ? detail : 'Intenta nuevamente.');
                this.cdr.detectChanges();
            }
        });
    }

    publishToEcommerce(): void {
        if (this.isLoading || !this.totalProducts) {
            return;
        }

        const selectedIds = Array.from(this.selectedProductIds);
        const scopeText = selectedIds.length
            ? `Se publicarán los ${selectedIds.length} productos seleccionados.`
            : `Se publicarán los ${this.totalProducts} productos activos del catálogo.`;
        this.swal
            .confirm(
                '¿Publicar productos en ecommerce?',
                `${scopeText} Los que ya estén publicados se conservarán y no se duplicarán.`
            )
            .then((result) => {
                if (!result.isConfirmed) {
                    return;
                }

                this.isLoading = true;
                const body = selectedIds.length ? { product_ids: selectedIds } : {};
                this.apiService.post<BulkPublishResponse>('/products/bulk-publish', body).subscribe({
                    next: (response) => {
                        this.clearSelection();
                        this.isLoading = false;
                        this.swal.success(
                            'Productos publicados',
                            `${response.published} producto(s) listos en ecommerce. ${response.already_published} ya estaban publicados.`
                        );
                        this.loadProducts();
                    },
                    error: (err) => {
                        this.isLoading = false;
                        const detail = err?.error?.detail;
                        this.swal.error(
                            'No se pudieron publicar los productos',
                            typeof detail === 'string' ? detail : 'Intenta nuevamente.'
                        );
                        this.cdr.detectChanges();
                    }
                });
            });
    }

    private showBulkDeleteResult(response: BulkDeleteResponse, partialTitle = 'Borrado parcial'): void {
        if (response.blocked.length || response.not_found.length) {
            const examples = response.blocked
                .slice(0, 3)
                .map((item) => `${item.name}: ${item.reasons.join(', ')}`)
                .join(' | ');
            const details = [
                `Eliminados definitivamente: ${response.deleted}.`,
                response.archived ? `Archivados por historial: ${response.archived}.` : '',
                `Conservados por seguridad: ${response.blocked.length}.`,
                response.not_found.length ? `No encontrados: ${response.not_found.length}.` : '',
                examples ? `Ejemplos: ${examples}.` : ''
            ]
                .filter(Boolean)
                .join(' ');
            this.swal.warning(partialTitle, details);
        } else {
            const archivedText = response.archived
                ? ` ${response.archived} producto(s) fueron archivados para conservar ventas, facturas e inventario.`
                : '';
            this.swal.success('Productos eliminados', `${response.deleted} producto(s) eliminado(s) correctamente.${archivedText}`);
        }
        this.loadProducts();
    }

    trackByFn(index: number, item: Product): string | undefined {
        void index;
        return item.id;
    }

    exportData(format: 'excel' | 'csv') {
        const params: Record<string, string> = {};
        if (this.searchQuery) params['search'] = this.searchQuery;
        this.exportService.download('/products/export', format, params);
    }
}
