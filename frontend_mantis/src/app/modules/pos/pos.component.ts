import { Component, OnInit, inject, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PosService, POSProduct, POSCheckout, POSCartItem } from '../../core/services/pos.service';
import { AuthService } from '../../core/services/auth.service';
import { ClientService } from '../clients/client.service';
import { BranchService } from '../../core/services/branch.service';
import Swal from 'sweetalert2';
import { ReceiptTicketComponent } from './components/receipt-ticket/receipt-ticket.component';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-pos',
    standalone: true,
    imports: [CommonModule, FormsModule, ReceiptTicketComponent, RouterModule],
    templateUrl: './pos.component.html',
    styleUrls: ['./pos.component.scss']
})
export class PosComponent implements OnInit {
    products: POSProduct[] = [];
    filteredProducts: POSProduct[] = [];
    searchQuery: string = '';

    // Cart
    cart: POSCartItem[] = [];
    selectedClientId: string = '';
    clients: any[] = [];

    // Auth & Context
    currentUser: any;
    currentBranchId: string = '';
    branches: any[] = [];

    // Category filters
    categories: string[] = [];
    selectedCategory: string = '';

    // Checkout Modal
    showCheckoutModal = false;
    paymentMethod: string = 'CASH';
    amountPaid: number | null = null;
    changeAmount: number = 0;

    // Receipt
    showReceipt = false;
    lastSale: any = null;

    // Mobile
    mobileTab: 'products' | 'cart' = 'products';

    private posService = inject(PosService);
    private authService = inject(AuthService);
    private clientService = inject(ClientService);
    private branchService = inject(BranchService);
    private cdr = inject(ChangeDetectorRef);

    @ViewChild('searchInput') searchInput!: ElementRef;

    ngOnInit() {
        this.currentUser = this.authService.currentUserValue;
        this.currentBranchId = this.currentUser?.branch_id || '';

        this.loadBranches();
        this.loadClients();
        if (this.currentBranchId) {
            this.loadProducts();
        }
    }

    loadBranches() {
        this.branchService.getBranches().subscribe(data => {
            this.branches = data;
            this.cdr.detectChanges();
        });
    }

    loadClients() {
        this.clientService.getClients().subscribe(data => {
            this.clients = data;
            this.cdr.detectChanges();
        });
    }

    onBranchChange() {
        this.cart = [];
        if (this.currentBranchId) {
            this.loadProducts();
        } else {
            this.products = [];
            this.filteredProducts = [];
        }
    }

    loadProducts() {
        this.posService.getProducts(this.currentBranchId).subscribe((data) => {
            this.products = data;
            // Extract unique category names
            const cats = data
                .map(p => p.category_name)
                .filter((c): c is string => !!c);
            this.categories = [...new Set(cats)].sort();
            this.selectedCategory = '';
            this.filteredProducts = data;
            this.cdr.detectChanges();
        });
    }

    selectCategory(cat: string) {
        this.selectedCategory = cat;
        this.filterProducts();
    }

    filterProducts() {
        const query = this.searchQuery.toLowerCase();
        this.filteredProducts = this.products.filter(p => {
            const matchesSearch = !query ||
                p.name.toLowerCase().includes(query) ||
                (p.barcode && p.barcode.includes(query)) ||
                (p.sku && p.sku.toLowerCase().includes(query));
            const matchesCategory = !this.selectedCategory || p.category_name === this.selectedCategory;
            return matchesSearch && matchesCategory;
        });

        // Exact barcode match -> auto add
        if (this.searchQuery && this.filteredProducts.length === 1 && this.filteredProducts[0].barcode === this.searchQuery) {
            this.addToCart(this.filteredProducts[0]);
            this.searchQuery = '';
            this.filterProducts();
        }
    }

    addToCart(product: POSProduct) {
        if (product.stock <= 0) {
            Swal.fire('Sin Stock', `El producto ${product.name} no tiene existencias.`, 'warning');
            return;
        }

        const existingItem = this.cart.find(item => item.product_id === product.id);
        if (existingItem) {
            if (existingItem.quantity >= product.stock) {
                Swal.fire('Límite', 'No puedes agregar más unidades de las disponibles en stock.', 'warning');
                return;
            }
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                product_id: product.id,
                quantity: 1,
                price: product.price,
                discount: 0,
                // Virtual property for UI
                _tempProduct: product
            } as any);
        }
        this.cdr.detectChanges();
    }

    updateQuantity(item: any, delta: number) {
        const product = this.products.find(p => p.id === item.product_id);
        if (!product) return;

        const newQty = item.quantity + delta;

        if (newQty <= 0) {
            this.removeItem(item);
        } else if (newQty > product.stock) {
            Swal.fire('Límite', 'Stock insuficiente', 'warning');
        } else {
            item.quantity = newQty;
        }
    }

    removeItem(item: any) {
        this.cart = this.cart.filter(i => i !== item);
    }

    clearCart() {
        this.cart = [];
    }

    get subtotal() {
        return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }

    get totalDiscount() {
        return this.cart.reduce((sum, item) => sum + item.discount, 0);
    }

    get total() {
        return this.subtotal - this.totalDiscount;
    }

    // --- Checkout Flow ---

    openCheckout() {
        if (this.cart.length === 0) return;
        if (!this.currentBranchId) {
            Swal.fire('Error', 'Debe seleccionar una sucursal.', 'error');
            return;
        }
        this.amountPaid = this.total; // Default exact amount
        this.paymentMethod = 'CASH';
        this.calculateChange();
        this.showCheckoutModal = true;
    }

    closeCheckout() {
        this.showCheckoutModal = false;
    }

    calculateChange() {
        if (this.amountPaid !== null) {
            this.changeAmount = this.amountPaid - this.total;
        }
    }

    setExactAmount() {
        this.amountPaid = this.total;
        this.calculateChange();
    }

    quickAmount(amount: number) {
        this.amountPaid = amount;
        this.calculateChange();
    }

    processPayment() {
        if (this.amountPaid === null || this.amountPaid < this.total) {
            if (this.paymentMethod !== 'CREDIT') {
                Swal.fire('Error', 'El monto pagado es menor al total de la venta.', 'error');
                return;
            }
        }

        const payload: POSCheckout = {
            branch_id: this.currentBranchId,
            client_id: this.selectedClientId || undefined,
            items: this.cart.map(i => ({
                product_id: i.product_id,
                quantity: i.quantity,
                price: i.price,
                discount: i.discount
            })),
            payment_method: this.paymentMethod,
            amount_paid: this.paymentMethod === 'CREDIT' ? 0 : this.amountPaid!
        };

        this.posService.checkout(payload).subscribe({
            next: (res) => {
                this.closeCheckout();

                // Prepare receipt data
                this.lastSale = {
                    id: res.sale_id,
                    total: res.total,
                    change: res.change,
                    items: this.cart.map(i => ({ ...i })),
                    payment_method: this.paymentMethod,
                    amount_paid: this.amountPaid,
                    date: new Date()
                };

                this.clearCart();
                this.loadProducts(); // Refresh stock
                this.showReceipt = true;

                Swal.fire({
                    title: 'Venta Completada',
                    text: `Cambio: $${res.change.toFixed(2)}`,
                    icon: 'success',
                    timer: 2500,
                    showConfirmButton: false
                }).then(() => {
                    // Do not auto-close receipt to let them print
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'Error al procesar el pago', 'error');
            }
        });
    }

    printReceipt() {
        window.print();
    }

    closeReceipt() {
        this.showReceipt = false;
        this.lastSale = null;
    }
}
