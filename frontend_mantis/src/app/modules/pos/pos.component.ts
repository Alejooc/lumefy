import { Component, OnInit, ViewChild, ElementRef, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { SweetAlertService } from '../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../core/services/auth.service';
import { ClientService } from '../clients/client.service';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { HttpParams } from '@angular/common/http';

@Component({
    selector: 'app-pos',
    templateUrl: './pos.component.html',
    styleUrls: ['./pos.component.scss'],
    standalone: false
})
export class PosComponent implements OnInit {
    // Data
    products: any[] = [];
    categories: any[] = [];
    cart: any[] = [];

    // State
    isLoading = false;
    isProcessing = false;
    productSearchInput$ = new Subject<string>();

    // Cart Totals
    subtotal = 0;
    tax = 0;
    total = 0;

    // Checkout
    paymentMethod = 'CASH';
    amountPaid = 0;
    change = 0;

    constructor(
        @Inject(ApiService) private api: ApiService,
        @Inject(SweetAlertService) private swal: SweetAlertService,
        @Inject(AuthService) private auth: AuthService,
        private clientService: ClientService // Standard DI
    ) { }

    currencySymbol = '$'; // Default
    clients: any[] = [];
    selectedClientId: string | null = null;
    clientSearch$ = new Subject<string>();

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
            }
        });

        this.loadProducts();
        this.loadClients();

        // Setup search
        this.productSearchInput$.pipe(
            debounceTime(400),
            distinctUntilChanged()
        ).subscribe(term => {
            this.loadProducts(term);
        });

        this.clientSearch$.pipe(
            debounceTime(400),
            distinctUntilChanged()
        ).subscribe(term => {
            this.loadClients(term);
        });
    }

    loadClients(term: string = '') {
        const params: any = {};
        if (term) params.q = term;
        this.clientService.getClients(params).subscribe(data => this.clients = data);
    }

    loadProducts(search: string = '') {
        this.isLoading = true;
        let params = new HttpParams();
        if (search) params = params.set('search', search);

        // We reuse the existing products endpoint which now supports search
        this.api.get<any[]>('/products', params).subscribe({
            next: (data) => {
                this.products = data;
                this.isLoading = false;
            },
            error: () => this.isLoading = false
        });
    }

    onSearch(event: any) {
        // ng-select search event
        if (event.term) {
            this.productSearchInput$.next(event.term);
        }
    }

    addToCart(product: any) {
        if (!product) return;

        const existingItem = this.cart.find(item => item.product.id === product.id);

        if (existingItem) {
            existingItem.quantity += 1;
            this.updateItemTotal(existingItem);
        } else {
            this.cart.push({
                product: product,
                quantity: 1,
                price: product.price,
                discount: 0,
                total: product.price
            });
        }

        this.calculateTotals();
        this.swal.toast('Agregado al carrito', 'success');
    }

    updateQuantity(item: any, change: number) {
        const newQty = item.quantity + change;
        if (newQty > 0) {
            item.quantity = newQty;
            this.updateItemTotal(item);
            this.calculateTotals();
        }
    }

    removeItem(index: number) {
        this.cart.splice(index, 1);
        this.calculateTotals();
    }

    updateItemTotal(item: any) {
        item.total = (item.price * item.quantity) - item.discount;
    }

    calculateTotals() {
        this.subtotal = this.cart.reduce((sum, item) => sum + item.total, 0);
        this.tax = this.subtotal * 0.16; // Example Tax
        this.total = this.subtotal; // For now simplified
        this.updateChange();
    }

    updateChange() {
        this.change = Math.max(0, this.amountPaid - this.total);
    }

    processSale() {
        if (this.cart.length === 0) {
            this.swal.warning('Carrito vacío', 'Agrega productos antes de cobrar.');
            return;
        }

        if (this.amountPaid < this.total && this.paymentMethod === 'CASH') {
            this.swal.warning('Pago insuficiente', 'El monto pagado es menor al total.');
            return;
        }

        this.isProcessing = true;

        const saleData = {
            branch_id: '7a287434-466e-4919-b25b-c9b09f87be81', // Default Branch
            client_id: this.selectedClientId,
            payment_method: this.paymentMethod,
            items: this.cart.map(item => ({
                product_id: item.product.id,
                quantity: item.quantity,
                price: item.price,
                discount: item.discount
            })),
            payments: [
                {
                    method: this.paymentMethod,
                    amount: this.total, // Full payment for now
                    reference: null
                }
            ]
        };

        this.api.post<any>('/pos', saleData).subscribe({
            next: (res) => {
                this.isProcessing = false;
                this.swal.success('Venta Exitosa', `Ticket #${res.id.substring(0, 8)}`);
                this.resetCart();
            },
            error: (err) => {
                this.isProcessing = false;
                console.error(err);
                this.swal.error('Error', 'No se pudo procesar la venta.');
            }
        });
    }

    resetCart() {
        this.cart = [];
        this.calculateTotals();
        this.amountPaid = 0;
        this.change = 0;
    }
}
