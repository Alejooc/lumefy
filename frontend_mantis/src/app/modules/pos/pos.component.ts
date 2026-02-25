import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { AuthService, User } from '../../core/services/auth.service';
import { BranchService, Branch } from '../../core/services/branch.service';
import { ClientService } from '../clients/client.service';
import { Client } from '../clients/client.model';
import { POSCartItem, POSCheckout, POSConfig, POSProduct, POSSession, POSSessionListItem, PosService } from '../../core/services/pos.service';
import { ReceiptTicketComponent } from './components/receipt-ticket/receipt-ticket.component';

interface PosReceipt {
    id: string;
    total: number;
    change: number;
    items: POSCartItem[];
    payment_method: string;
    amount_paid: number | null;
    date: Date;
}

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
    searchQuery = '';

    cart: POSCartItem[] = [];
    selectedClientId = '';
    clients: Client[] = [];

    currentUser: User | null = null;
    currentBranchId = '';
    branches: Branch[] = [];

    categories: string[] = [];
    selectedCategory = '';

    currentSession: POSSession | null = null;
    posConfig: POSConfig = {
        show_sessions_manager: true,
        session_visibility_scope: 'branch',
        allow_multiple_open_sessions_per_branch: true,
        allow_enter_other_user_session: false,
        require_manager_for_void: true
    };
    sessions: POSSessionListItem[] = [];
    showSessionsModal = false;
    sessionsFilter: '' | 'OPEN' | 'CLOSED' = 'OPEN';
    loadingSessions = false;

    showCheckoutModal = false;
    paymentMethod = 'CASH';
    amountPaid: number | null = null;
    changeAmount = 0;

    showReceipt = false;
    lastSale: PosReceipt | null = null;

    mobileTab: 'products' | 'cart' = 'products';
    private readonly branchStorageKey = 'pos_branch_id';

    private posService = inject(PosService);
    private authService = inject(AuthService);
    private clientService = inject(ClientService);
    private branchService = inject(BranchService);
    private cdr = inject(ChangeDetectorRef);

    @ViewChild('searchInput') searchInput!: ElementRef;

    ngOnInit() {
        this.currentUser = this.authService.currentUserValue;
        const storedBranch = localStorage.getItem(this.branchStorageKey) || '';
        this.currentBranchId = this.currentUser?.branch_id || storedBranch;

        this.loadPosConfig();
        this.loadBranches();
        this.loadClients();
    }

    loadPosConfig() {
        this.posService.getConfig().subscribe({
            next: (cfg) => {
                this.posConfig = cfg;
                this.cdr.detectChanges();
            },
            error: () => {
                this.cdr.detectChanges();
            }
        });
    }

    loadBranches() {
        this.branchService.getBranches().subscribe((data) => {
            this.branches = data;
            if (!this.currentBranchId && this.branches.length > 0) {
                this.currentBranchId = this.branches[0].id;
            }
            if (this.currentBranchId && !this.branches.some((b) => b.id === this.currentBranchId)) {
                this.currentBranchId = this.branches[0]?.id || '';
            }
            if (this.currentBranchId) {
                localStorage.setItem(this.branchStorageKey, this.currentBranchId);
                this.loadProducts();
                this.loadCurrentSession();
                this.loadSessions();
            }
            this.cdr.detectChanges();
        });
    }

    loadClients() {
        this.clientService.getClients().subscribe((data) => {
            this.clients = data;
            this.cdr.detectChanges();
        });
    }

    onBranchChange() {
        this.cart = [];
        this.currentSession = null;
        this.sessions = [];
        if (this.currentBranchId) {
            localStorage.setItem(this.branchStorageKey, this.currentBranchId);
        } else {
            localStorage.removeItem(this.branchStorageKey);
        }
        if (this.currentBranchId) {
            this.loadProducts();
            this.loadCurrentSession();
            this.loadSessions();
        } else {
            this.products = [];
            this.filteredProducts = [];
        }
    }

    loadCurrentSession() {
        if (!this.currentBranchId) return;
        this.posService.getCurrentSession(this.currentBranchId).subscribe({
            next: (session) => {
                this.currentSession = session;
                this.cdr.detectChanges();
            },
            error: () => {
                this.currentSession = null;
                this.cdr.detectChanges();
            }
        });
    }

    loadProducts() {
        this.posService.getProducts(this.currentBranchId).subscribe((data) => {
            this.products = data;
            const cats = data.map((p) => p.category_name).filter((c): c is string => !!c);
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
        this.filteredProducts = this.products.filter((p) => {
            const matchesSearch = !query || p.name.toLowerCase().includes(query) || (p.barcode && p.barcode.includes(query)) || (p.sku && p.sku.toLowerCase().includes(query));
            const matchesCategory = !this.selectedCategory || p.category_name === this.selectedCategory;
            return matchesSearch && matchesCategory;
        });

        if (this.searchQuery && this.filteredProducts.length === 1 && this.filteredProducts[0].barcode === this.searchQuery) {
            this.addToCart(this.filteredProducts[0]);
            this.searchQuery = '';
            this.filterProducts();
        }
    }

    addToCart(product: POSProduct) {
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de vender en POS.', 'warning');
            return;
        }
        if (product.stock <= 0) {
            Swal.fire('Sin Stock', `El producto ${product.name} no tiene existencias.`, 'warning');
            return;
        }

        const existingItem = this.cart.find((item) => item.product_id === product.id);
        if (existingItem) {
            if (existingItem.quantity >= product.stock) {
                Swal.fire('Limite', 'No puedes agregar mas unidades de las disponibles en stock.', 'warning');
                return;
            }
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                product_id: product.id,
                quantity: 1,
                price: product.price,
                discount: 0,
                _tempProduct: product
            });
        }
        this.cdr.detectChanges();
    }

    updateQuantity(item: POSCartItem, delta: number) {
        const product = this.products.find((p) => p.id === item.product_id);
        if (!product) return;

        const newQty = item.quantity + delta;
        if (newQty <= 0) {
            this.removeItem(item);
        } else if (newQty > product.stock) {
            Swal.fire('Limite', 'Stock insuficiente', 'warning');
        } else {
            item.quantity = newQty;
        }
    }

    removeItem(item: POSCartItem) {
        this.cart = this.cart.filter((i) => i !== item);
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

    openCheckout() {
        if (this.cart.length === 0) return;
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de cobrar.', 'warning');
            return;
        }
        if (!this.currentBranchId) {
            Swal.fire('Error', 'Debe seleccionar una sucursal.', 'error');
            return;
        }
        this.amountPaid = this.total;
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
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de cobrar.', 'warning');
            return;
        }
        if (this.amountPaid === null || this.amountPaid < this.total) {
            if (this.paymentMethod !== 'CREDIT') {
                Swal.fire('Error', 'El monto pagado es menor al total de la venta.', 'error');
                return;
            }
        }

        const payload: POSCheckout = {
            branch_id: this.currentBranchId,
            client_id: this.selectedClientId || undefined,
            items: this.cart.map((i) => ({
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

                this.lastSale = {
                    id: res.sale_id,
                    total: res.total,
                    change: res.change,
                    items: this.cart.map((i) => ({ ...i })),
                    payment_method: this.paymentMethod,
                    amount_paid: this.amountPaid,
                    date: new Date()
                };

                this.clearCart();
                this.loadProducts();
                this.loadCurrentSession();
                this.loadSessions();
                this.showReceipt = true;

                Swal.fire({
                    title: 'Venta Completada',
                    text: `Cambio: $${res.change.toFixed(2)}`,
                    icon: 'success',
                    timer: 2500,
                    showConfirmButton: false
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'Error al procesar el pago', 'error');
            }
        });
    }

    openCashSession() {
        if (!this.currentBranchId) {
            Swal.fire('Sucursal requerida', 'Selecciona una sucursal antes de abrir caja.', 'warning');
            return;
        }
        Swal.fire({
            title: 'Abrir caja',
            html: `
              <label class="form-label">Monto inicial</label>
              <input id="opening_amount" type="number" step="0.01" min="0" class="swal2-input" value="0" />
              <label class="form-label mt-2">Nota (opcional)</label>
              <input id="opening_note" type="text" class="swal2-input" placeholder="Ej: Fondo inicial turno manana" />
            `,
            showCancelButton: true,
            confirmButtonText: 'Abrir caja',
            preConfirm: () => {
                const amountRaw = (document.getElementById('opening_amount') as HTMLInputElement)?.value;
                const note = (document.getElementById('opening_note') as HTMLInputElement)?.value;
                const openingAmount = Number(amountRaw || 0);
                if (openingAmount < 0) {
                    Swal.showValidationMessage('El monto inicial no puede ser negativo.');
                    return null;
                }
                return { openingAmount, note };
            }
        }).then((result) => {
            if (!result.isConfirmed || !result.value) return;
            this.posService.openSession(this.currentBranchId, result.value.openingAmount, result.value.note).subscribe({
                next: (session) => {
                    this.currentSession = session;
                    this.loadSessions();
                    this.cdr.detectChanges();
                    Swal.fire('Caja activa', 'Caja lista para vender en POS.', 'success');
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo abrir la caja.', 'error');
                }
            });
        });
    }

    closeCashSession() {
        if (!this.currentSession) {
            Swal.fire('Sin caja abierta', 'No hay una sesion de caja activa.', 'info');
            return;
        }
        Swal.fire({
            title: 'Cerrar caja',
            html: `
              <p class="mb-2 text-start"><strong>Esperado:</strong> ${this.currentSession.expected_amount.toFixed(2)}</p>
              <label class="form-label">Efectivo contado</label>
              <input id="counted_amount" type="number" step="0.01" min="0" class="swal2-input" value="${this.currentSession.expected_amount.toFixed(2)}" />
              <label class="form-label mt-2">Nota de cierre (opcional)</label>
              <input id="closing_note" type="text" class="swal2-input" placeholder="Ej: Diferencia por redondeos" />
            `,
            showCancelButton: true,
            confirmButtonText: 'Cerrar caja',
            preConfirm: () => {
                const countedRaw = (document.getElementById('counted_amount') as HTMLInputElement)?.value;
                const note = (document.getElementById('closing_note') as HTMLInputElement)?.value;
                const countedAmount = Number(countedRaw || 0);
                if (countedAmount < 0) {
                    Swal.showValidationMessage('El efectivo contado no puede ser negativo.');
                    return null;
                }
                return { countedAmount, note };
            }
        }).then((result) => {
            if (!result.isConfirmed || !result.value || !this.currentSession) return;
            this.posService.closeSession(this.currentSession.id, result.value.countedAmount, result.value.note).subscribe({
                next: (session) => {
                    const diff = session.over_short;
                    this.currentSession = null;
                    this.cart = [];
                    this.loadSessions();
                    this.cdr.detectChanges();
                    Swal.fire(
                        'Caja cerrada',
                        `Esperado: ${session.expected_amount.toFixed(2)} | Contado: ${session.counted_amount.toFixed(2)} | Diferencia: ${diff.toFixed(2)}`,
                        diff === 0 ? 'success' : 'warning'
                    );
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo cerrar la caja.', 'error');
                }
            });
        });
    }

    printReceipt() {
        window.print();
    }

    closeReceipt() {
        this.showReceipt = false;
        this.lastSale = null;
    }

    voidLastSale() {
        if (!this.lastSale) return;
        Swal.fire({
            title: 'Anular venta',
            html: `
              <label class="form-label">Motivo</label>
              <input id="void_reason" type="text" class="swal2-input" placeholder="Ej: Error de cobro" />
            `,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Anular',
            preConfirm: () => {
                const reason = (document.getElementById('void_reason') as HTMLInputElement)?.value;
                return reason || 'Anulacion solicitada desde POS';
            }
        }).then((result) => {
            if (!result.isConfirmed || !this.lastSale) return;
            this.posService.voidSale(this.lastSale.id, result.value).subscribe({
                next: (res) => {
                    Swal.fire('Venta anulada', res.detail, 'success');
                    this.loadProducts();
                    this.loadCurrentSession();
                    this.loadSessions();
                    this.closeReceipt();
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo anular la venta.', 'error');
                }
            });
        });
    }

    loadSessions() {
        this.loadingSessions = true;
        const status = this.sessionsFilter || undefined;
        this.posService.listSessions(this.currentBranchId || undefined, status).subscribe({
            next: (rows) => {
                this.sessions = rows;
                this.loadingSessions = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.sessions = [];
                this.loadingSessions = false;
                this.cdr.detectChanges();
            }
        });
    }

    openSessionsManager() {
        if (!this.posConfig.show_sessions_manager) {
            Swal.fire('No disponible', 'El gestor de cajas esta deshabilitado en configuracion POS.', 'info');
            return;
        }
        this.showSessionsModal = true;
        this.loadSessions();
    }

    closeSessionsManager() {
        this.showSessionsModal = false;
    }

    onSessionFilterChange(filter: '' | 'OPEN' | 'CLOSED') {
        this.sessionsFilter = filter;
        this.loadSessions();
    }

    enterSession(session: POSSessionListItem) {
        if (!this.currentUser) return;
        if (session.status !== 'OPEN') {
            Swal.fire('Caja cerrada', 'Solo puedes entrar en cajas abiertas.', 'info');
            return;
        }
        if (session.user_id !== this.currentUser.id && !this.posConfig.allow_enter_other_user_session) {
            Swal.fire('No permitido', 'Solo puedes entrar en tu propia caja.', 'warning');
            return;
        }
        this.currentBranchId = session.branch_id;
        localStorage.setItem(this.branchStorageKey, this.currentBranchId);
        this.loadProducts();
        this.loadCurrentSession();
        this.showSessionsModal = false;
    }

    viewSessionStats(session: POSSessionListItem) {
        this.posService.getSessionStats(session.id).subscribe({
            next: (stats) => {
                Swal.fire({
                    title: `Caja ${stats.status === 'OPEN' ? 'abierta' : 'cerrada'}`,
                    html: `
                      <div style="text-align:left;line-height:1.5">
                        <div><strong>Sucursal:</strong> ${stats.branch_name || '-'}</div>
                        <div><strong>Cajero:</strong> ${stats.user_name || '-'}</div>
                        <div><strong>Apertura:</strong> ${new Date(stats.opened_at).toLocaleString()}</div>
                        <div><strong>Cierre:</strong> ${stats.closed_at ? new Date(stats.closed_at).toLocaleString() : '-'}</div>
                        <hr/>
                        <div><strong>Ventas:</strong> ${stats.total_sales.toFixed(2)}</div>
                        <div><strong>Transacciones:</strong> ${stats.transactions_count}</div>
                        <div><strong>Ticket promedio:</strong> ${stats.average_ticket.toFixed(2)}</div>
                        <div><strong>Efectivo:</strong> ${stats.cash_sales_total.toFixed(2)}</div>
                        <div><strong>Tarjeta:</strong> ${stats.card_sales_total.toFixed(2)}</div>
                        <div><strong>Credito:</strong> ${stats.credit_sales_total.toFixed(2)}</div>
                        <hr/>
                        <div><strong>Monto inicial:</strong> ${stats.opening_amount.toFixed(2)}</div>
                        <div><strong>Esperado en caja:</strong> ${stats.expected_amount.toFixed(2)}</div>
                        <div><strong>Contado:</strong> ${stats.counted_amount.toFixed(2)}</div>
                        <div><strong>Diferencia:</strong> ${stats.over_short.toFixed(2)}</div>
                      </div>
                    `,
                    width: 620
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'No se pudieron cargar las estadisticas de caja.', 'error');
            }
        });
    }
}
