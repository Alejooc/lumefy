import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';
import { PermissionService } from '../../../core/services/permission.service';
import { ExportService } from '../../../core/services/export.service';

@Component({
    selector: 'app-product-list',
    standalone: false,
    templateUrl: './product-list.component.html',
    styleUrls: ['./product-list.component.scss']
})
export class ProductListComponent implements OnInit {
    products: any[] = [];
    isLoading = false;
    searchQuery = '';

    currencySymbol = '$';
    canAccessWizard = false;

    constructor(
        private apiService: ApiService,
        private swal: SweetAlertService,
        private auth: AuthService,
        private permissionService: PermissionService,
        private cdr: ChangeDetectorRef,
        private exportService: ExportService
    ) { }

    ngOnInit(): void {
        this.canAccessWizard = this.permissionService.hasAnyPermission(['manage_company', 'manage_users']);

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
        this.apiService.get<any[]>(`/products${params}`).subscribe({
            next: (data) => {
                this.products = data;
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
        this.loadProducts();
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
                        this.swal.error('Error', 'No se pudo eliminar el producto.');
                        this.isLoading = false;
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }

    trackByFn(index: number, item: any): any {
        return item.id;
    }

    exportData(format: 'excel' | 'csv') {
        const params: Record<string, string> = {};
        if (this.searchQuery) params['search'] = this.searchQuery;
        this.exportService.download('/products/export', format, params);
    }
}
