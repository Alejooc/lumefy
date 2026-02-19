import { Component, OnInit, ViewChild, ElementRef, Inject, ChangeDetectorRef, HostListener } from '@angular/core';
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

    // Inventory
    inventoryMap: { [key: string]: number } = {};
    parkedOrders: any[] = [];
    branches: any[] = [];
    selectedBranchId: string | null = null;

    // Scanner
    barcodeBuffer = '';
    barcodeTimeout: any;

    @ViewChild('scannerInput') scannerInput!: ElementRef;

    currencySymbol = '$'; // Default
    clients: any[] = [];
    selectedClientId: string | null = null;
    clientSearch$ = new Subject<string>();

    selectedCategory: any = 'ALL';
    filteredProducts: any[] = [];

    constructor(
        @Inject(ApiService) private api: ApiService,
        @Inject(SweetAlertService) private swal: SweetAlertService,
        @Inject(AuthService) private auth: AuthService,
        private clientService: ClientService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        // Load data
        this.loadBranches(); // Load branches first, then inventory
        this.loadProducts();
        this.loadCategories();
        this.loadClients();
        this.loadParkedOrders();

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

    // --- Barcode Scanner Logic ---
    @HostListener('window:keydown', ['$event'])
    handleKeyboardEvent(event: KeyboardEvent) {
        if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
            return;
        }

        if (event.key === 'Enter') {
            if (this.barcodeBuffer.length > 2) {
                this.handleScan(this.barcodeBuffer);
            }
            this.barcodeBuffer = '';
        } else if (event.key.length === 1) {
            this.barcodeBuffer += event.key;
            clearTimeout(this.barcodeTimeout);
            this.barcodeTimeout = setTimeout(() => {
                this.barcodeBuffer = '';
            }, 100);
        }
    }

    handleScan(code: string) {
        const product = this.products.find(p => p.barcode === code || p.sku === code);
        if (product) {
            this.addToCart(product);
            this.swal.toast(`Escaneado: ${product.name}`, 'success');
        } else {
            this.swal.toast(`Producto no encontrado: ${code}`, 'error');
        }
    }

    // --- Inventory Logic ---
    loadBranches() {
        this.api.get<any[]>('/branches').subscribe(data => {
            this.branches = data;
            if (this.branches.length > 0) {
                // Default to first branch
                this.selectedBranchId = this.branches[0].id;
                this.loadInventory();
            } else {
                this.swal.warning('Sin Sucursales', 'No hay sucursales configuradas.');
            }
        });
    }

    loadInventory() {
        if (!this.selectedBranchId) return;

        this.api.get<any[]>(`/inventory?branch_id=${this.selectedBranchId}`).subscribe(data => {
            this.inventoryMap = {};
            data.forEach(item => {
                this.inventoryMap[item.product.id] = item.quantity;
            });
            this.cdr.detectChanges();
        });
    }

    getProductStock(product: any): number {
        if (product.track_inventory === false) return 9999;
        return this.inventoryMap[product.id] || 0;
    }

    // --- Data Loading ---
    loadCategories() {
        this.api.get<any[]>('/categories').subscribe(data => {
            this.categories = [{ id: 'ALL', name: 'Todos' }, ...data];
            this.cdr.detectChanges();
        });
    }

    loadClients(term: string = '') {
        const params: any = {};
        if (term) params.q = term;
        this.clientService.getClients(params).subscribe(data => {
            this.clients = data;
            this.cdr.detectChanges();
        });
    }

    loadProducts(search: string = '') {
        this.isLoading = true;
        let params = new HttpParams();
        if (search) params = params.set('search', search);

        this.api.get<any[]>('/products', params).subscribe({
            next: (data) => {
                this.products = data;
                this.filterProducts();
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }

    selectCategory(catId: any) {
        this.selectedCategory = catId;
        this.filterProducts();
    }

    filterProducts() {
        if (this.selectedCategory === 'ALL') {
            this.filteredProducts = this.products;
        } else {
            this.filteredProducts = this.products.filter(p => p.category_id === this.selectedCategory);
        }
    }

    onSearch(event: any) {
        if (event.term) {
            this.productSearchInput$.next(event.term);
        }
    }

    // --- Cart Actions ---
    addToCart(product: any) {
        if (!product) return;

        // Check for Variants
        if (product.variants && product.variants.length > 0) {
            this.promptVariantSelection(product);
            return;
        }

        this.addItemToCart(product);
    }

    promptVariantSelection(product: any) {
        const options = {};
        product.variants.forEach(v => {
            const priceInfo = v.price_extra > 0 ? ` (+${this.currencySymbol}${v.price_extra})` : '';
            options[v.id] = `${v.name}${priceInfo}`;
        });

        this.swal.input({
            title: 'Selecciona una Variante',
            text: product.name,
            input: 'select',
            inputOptions: options,
            inputPlaceholder: 'Elige una opción',
            showCancelButton: true
        }).then((result: any) => {
            if (result.isConfirmed && result.value) {
                const selectedVariant = product.variants.find(v => v.id === result.value);
                this.addItemToCart(product, selectedVariant);
            }
        });
    }

    addItemToCart(product: any, variant: any = null) {
        const productKey = variant ? `${product.id}-${variant.id}` : product.id;
        // Use variant price if available, logic: Base + Extra
        // Or if variant has explicit price? Model says price_extra.
        const finalPrice = variant ? (product.price + variant.price_extra) : product.price;
        const displayName = variant ? `${product.name} (${variant.name})` : product.name;

        // Stock Check
        // Ideally check variant stock. But backend only tracks PRODUCT stock for now?
        // Let's assume stock is on main product or handle later.
        // For now, use main product stock logic.
        const currentStock = this.getProductStock(product);

        // Find existing item by Key (Product + Variant)
        // We need to change how we identify items in cart.
        // Let's add 'key' property to cart item.
        const existingItem = this.cart.find(item => item.key === productKey);
        const currentQtyInCart = existingItem ? existingItem.quantity : 0;

        if (product.track_inventory && (currentQtyInCart + 1 > currentStock)) {
            this.swal.error('¡Ups! Sin Stock', `Este producto está agotado o no hay suficiente cantidad disponible.\n(Stock: ${currentStock})`);
            return;
        }

        if (existingItem) {
            existingItem.quantity += 1;
            this.updateItemTotal(existingItem);
        } else {
            this.cart.push({
                key: productKey, // Unique ID for cart
                product: product,
                variant: variant, // Store variant info
                name: displayName, // Display name
                quantity: 1,
                price: finalPrice,
                discount: 0,
                total: finalPrice
            });
        }

        this.calculateTotals();
        this.swal.toast('Agregado al carrito', 'success');
        this.cdr.detectChanges();
    }

    updateQuantity(item: any, change: number) {
        const newQty = item.quantity + change;

        // Check stock for increment
        if (change > 0 && item.product.track_inventory) {
            const stock = this.getProductStock(item.product);
            if (newQty > stock) {
                this.swal.toast('Stock insuficiente', 'warning');
                return;
            }
        }

        if (newQty > 0) {
            item.quantity = newQty;
            this.updateItemTotal(item);
            this.calculateTotals();
            this.cdr.detectChanges();
        }
    }

    removeItem(index: number) {
        this.cart.splice(index, 1);
        this.calculateTotals();
        this.cdr.detectChanges();
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

    resetCart() {
        this.cart = [];
        this.calculateTotals();
        this.amountPaid = 0;
        this.change = 0;
    }

    // --- Parking Logic ---
    parkOrder() {
        if (this.cart.length === 0) return;

        const order = {
            id: Date.now(),
            cart: [...this.cart],
            client: this.selectedClientId,
            date: new Date(),
            total: this.total // Save total for display
        };

        this.parkedOrders.push(order);
        this.saveParkedOrders();
        this.resetCart();
        this.swal.toast('Orden guardada', 'info');
    }

    showParkedOrders() {
        if (this.parkedOrders.length === 0) {
            this.swal.toast('No hay ordenes pendientes', 'info');
            return;
        }

        const listHtml = this.parkedOrders.map((o, index) => {
            const dateStr = new Date(o.date).toLocaleTimeString();
            return `<li class="list-group-item d-flex justify-content-between align-items-center">
                <span>Orden #${o.id.toString().slice(-4)} - ${this.currencySymbol}${o.total?.toFixed(2) || '0.00'}</span>
                <button class="btn btn-sm btn-primary restore-btn" data-index="${index}">Restaurar</button>
            </li>`;
        }).join('');

        this.swal.input({
            title: 'Ordenes Pendientes',
            html: `<ul class="list-group text-start">${listHtml}</ul>`,
            showConfirmButton: false,
            showCloseButton: true,
            didOpen: () => {
                // Attach click events manually since Swal removes angular bindings
                const buttons = document.querySelectorAll('.restore-btn');
                buttons.forEach((btn: any) => {
                    btn.addEventListener('click', () => {
                        const index = btn.getAttribute('data-index');
                        const order = this.parkedOrders[index];
                        this.swal.close(); // Close modal
                        this.unparkOrder(order);
                    });
                });
            }
        });
    }

    unparkOrder(order: any) {
        if (this.cart.length > 0) {
            this.swal.confirm('Reemplazar orden actual?', 'Se perderán los items actuales.').then(res => {
                if (res.isConfirmed) {
                    this.forceUnpark(order);
                }
            });
        } else {
            this.forceUnpark(order);
        }
    }

    forceUnpark(order: any) {
        this.cart = [...order.cart]; // Create a new reference
        this.selectedClientId = order.client;
        this.parkedOrders = this.parkedOrders.filter(o => o.id !== order.id);
        this.saveParkedOrders();
        this.calculateTotals();
        this.swal.toast('Orden restaurada', 'success');
        this.cdr.detectChanges(); // Force UI update
    }

    saveParkedOrders() {
        localStorage.setItem('pos_parked_orders', JSON.stringify(this.parkedOrders));
    }

    loadParkedOrders() {
        const stored = localStorage.getItem('pos_parked_orders');
        if (stored) {
            this.parkedOrders = JSON.parse(stored);
        }
    }

    // --- Discount Logic ---
    applyDiscount() {
        this.swal.input({
            title: 'Descuento Global',
            text: 'Ingresa porcentaje (%) o monto fijo ($)',
            input: 'text',
            inputPlaceholder: 'Ej: 10% o 500'
        }).then((result: any) => {
            if (result.isConfirmed && result.value) {
                const val = result.value;
                if (val.includes('%')) {
                    const pct = parseFloat(val) / 100;
                    this.cart.forEach(item => {
                        item.discount = item.price * pct * item.quantity;
                        this.updateItemTotal(item);
                    });
                } else {
                    const amount = parseFloat(val);
                    this.cart.push({
                        product: { name: 'Descuento Manual', price: -amount, id: 'DISC', track_inventory: false },
                        quantity: 1,
                        price: -amount,
                        discount: 0,
                        total: -amount
                    });
                }
                this.calculateTotals();
            }
        });
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

        // Generate Notes with Variant Info
        const variantNotes = this.cart
            .filter(item => item.variant)
            .map(item => `- ${item.quantity}x ${item.name}`)
            .join('\n');

        const finalNotes = variantNotes ? `Variantes:\n${variantNotes}` : '';

        const saleData = {
            branch_id: this.selectedBranchId, // Use selected branch
            client_id: this.selectedClientId,
            payment_method: this.paymentMethod,
            notes: finalNotes, // Send variant info here!
            items: this.cart.map(item => ({
                product_id: item.product.id,
                quantity: item.quantity,
                price: item.price,
                discount: item.discount
            })),
            payments: [
                {
                    method: this.paymentMethod,
                    amount: this.total,
                    reference: null
                }
            ]
        };

        this.api.post<any>('/pos', saleData).subscribe({
            next: (res) => {
                this.isProcessing = false;
                this.swal.success('Venta Exitosa', `Ticket #${res.id.substring(0, 8)}`);
                this.resetCart();
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.isProcessing = false;
                console.error(err);
                this.swal.error('Error', 'No se pudo procesar la venta.');
                this.cdr.detectChanges();
            }
        });
    }
}
