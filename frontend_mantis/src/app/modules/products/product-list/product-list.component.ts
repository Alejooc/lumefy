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
    blocked: BulkDeleteBlockedProduct[];
    not_found: string[];
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
        const params = this.searchQuery ? `?search=${encodeURIComponent(this.searchQuery)}` : '';
        this.apiService.get<Product[]>(`/products${params}`).subscribe({
            next: (data) => {
                this.products = data;
                const visibleIds = new Set(
                    data.map((product) => product.id).filter((id): id is string => Boolean(id))
                );
                this.selectedProductIds = new Set(
                    Array.from(this.selectedProductIds).filter((id) => visibleIds.has(id))
                );
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
        this.loadProducts();
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
                            if (response.blocked.length || response.not_found.length) {
                                const examples = response.blocked
                                    .slice(0, 3)
                                    .map((item) => `${item.name}: ${item.reasons.join(', ')}`)
                                    .join(' | ');
                                const details = [
                                    `Eliminados: ${response.deleted}.`,
                                    `Conservados por seguridad: ${response.blocked.length}.`,
                                    response.not_found.length ? `No encontrados: ${response.not_found.length}.` : '',
                                    examples ? `Ejemplos: ${examples}.` : ''
                                ]
                                    .filter(Boolean)
                                    .join(' ');
                                this.swal.warning('Borrado parcial', details);
                            } else {
                                this.swal.success(
                                    'Productos eliminados',
                                    `${response.deleted} producto(s) eliminado(s) correctamente.`
                                );
                            }
                            this.loadProducts();
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
