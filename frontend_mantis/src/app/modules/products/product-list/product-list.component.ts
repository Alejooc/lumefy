import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
    selector: 'app-product-list',
    standalone: false,
    templateUrl: './product-list.component.html',
    styleUrls: ['./product-list.component.scss']
})
export class ProductListComponent implements OnInit {
    products: any[] = [];
    isLoading = false;

    currencySymbol = '$';

    constructor(
        private apiService: ApiService,
        private cdr: ChangeDetectorRef,
        private swal: SweetAlertService,
        private auth: AuthService
    ) { }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
            }
        });

        this.loadProducts();
    }

    loadProducts() {
        this.isLoading = true;
        this.apiService.get<any[]>('/products').subscribe({
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

    deleteProduct(id: string) {
        this.swal.confirmDelete().then((confirmed) => {
            if (confirmed) {
                this.isLoading = true;
                this.apiService.delete(`/products/${id}`).subscribe({
                    next: () => {
                        this.swal.success('Deleted!', 'Product has been deleted.');
                        this.loadProducts();
                    },
                    error: (err) => {
                        console.error('Error deleting product', err);
                        this.swal.error('Error', 'Could not delete product.');
                        this.isLoading = false;
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }
}
